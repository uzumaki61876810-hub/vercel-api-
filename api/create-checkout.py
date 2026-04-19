"""
Stripe Checkout Session 作成エンドポイント
POST /api/create-checkout

フォームデータを受け取り → 四柱推命/占星術を計算 →
Stripe Checkout Session（メタデータ付き）を作成 → URL を返す
"""
import os, sys, json
from datetime import date as _date
from http.server import BaseHTTPRequestHandler
import stripe

# ── 計算モジュール ──
KANS  = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
SHIS  = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
SIGNS = ['牡羊座','牡牛座','双子座','蟹座','獅子座','乙女座',
         '天秤座','蠍座','射手座','山羊座','水瓶座','魚座']

KAN_INFO = [
    {'g':'木','i':'陽'},{'g':'木','i':'陰'},{'g':'火','i':'陽'},{'g':'火','i':'陰'},
    {'g':'土','i':'陽'},{'g':'土','i':'陰'},{'g':'金','i':'陽'},{'g':'金','i':'陰'},
    {'g':'水','i':'陽'},{'g':'水','i':'陰'},
]
ZOKKAN = {'子':8,'丑':5,'寅':0,'卯':1,'辰':4,'巳':2,'午':3,'未':5,'申':6,'酉':7,'戌':4,'亥':8}
JISHI  = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
JUUNUN = ['長生','沐浴','冠帯','建禄','帝旺','衰','病','死','墓','絶','胎','養']
JUENERGY = {'長生':9,'沐浴':7,'冠帯':10,'建禄':11,'帝旺':12,'衰':8,'病':4,'死':2,'墓':5,'絶':1,'胎':3,'養':6}
CHOUSEI = {0:'亥',1:'午',2:'寅',3:'酉',4:'寅',5:'酉',6:'巳',7:'子',8:'申',9:'卯'}
REVERSE = [False,True,False,True,False,True,False,True,False,True]


def _sun_sign(year, month, day):
    cuts = [(1,20,9),(2,19,10),(3,21,0),(4,20,1),(5,21,2),(6,21,3),
            (7,23,4),(8,23,5),(9,23,6),(10,23,7),(11,22,8),(12,22,9)]
    s = 8
    for m,d,sg in cuts:
        if month > m or (month == m and day >= d):
            s = sg
    if month == 12 and day >= 22:
        s = 9
    return SIGNS[s]


def _to_jd(year, month, day, hour=12.0):
    y, m = year, month
    if m <= 2: y -= 1; m += 12
    A = y // 100
    B = 2 - A + A // 4
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + day + B - 1524.5 + hour/24


def _moon_sign(year, month, day, hour=12.0):
    jd = _to_jd(year, month, day, hour)
    ml = (218.316 + 13.176396 * (jd - 2451545.0)) % 360
    if ml < 0: ml += 360
    return SIGNS[int(ml/30)]


def _year_pillar(year):
    ki = ((year-4)%10+10)%10
    si = ((year-4)%12+12)%12
    return KANS[ki]+SHIS[si], ki, si


def _month_pillar(year, month):
    yk = ((year-4)%10+10)%10
    sk = [2,4,6,8,0,2,4,6,8,0][yk]
    off = (month-3+12)%12
    ki = (sk+off)%10
    si = (off+2)%12
    return KANS[ki]+SHIS[si], ki, si


def _day_pillar(year, month, day):
    diff = (_date(year, month, day) - _date(1900, 1, 1)).days + 10
    ki = diff % 10
    si = diff % 12
    return KANS[ki]+SHIS[si], ki, si


def _tsuhen(dk, tk):
    gg = ['木','火','土','金','水']
    dg = gg.index(KAN_INFO[dk]['g'])
    tg = gg.index(KAN_INFO[tk]['g'])
    si = KAN_INFO[dk]['i'] == KAN_INFO[tk]['i']
    if dg == tg: return '比肩' if si else '劫財'
    if (dg+1)%5 == tg: return '食神' if si else '傷官'
    if (dg+2)%5 == tg: return '偏財' if si else '正財'
    if (tg+2)%5 == dg: return '偏官' if si else '正官'
    if (tg+1)%5 == dg: return '偏印' if si else '印綬'
    return '不明'


def _juunun(dk, shi_char):
    cs = CHOUSEI[dk]
    si = JISHI.index(cs)
    ti = JISHI.index(shi_char)
    diff = (ti-si+12)%12 if not REVERSE[dk] else (si-ti+12)%12
    return JUUNUN[diff]


def _composite(day_star, month_star):
    def cat(s):
        if s in ['比肩','劫財']: return 'hikken'
        if s in ['食神','傷官']: return 'shokusin'
        if s in ['偏財','正財']: return 'seizan'
        if s in ['偏官','正官']: return 'seikan'
        return 'seiin'
    names = {
        'hikken_hikken':'孤高の独立者','hikken_shokusin':'才能で独立する開拓者',
        'hikken_seizan':'実力で富を築く商人','hikken_seikan':'自律した指揮官',
        'hikken_seiin':'孤高の思想家','shokusin_hikken':'自由な表現者',
        'shokusin_shokusin':'感性の商人','shokusin_seizan':'表現で稼ぐ才能人',
        'shokusin_seikan':'スター性のある実行者','shokusin_seiin':'直感で突き抜けるアーティスト',
        'seizan_hikken':'自立した財の人','seizan_shokusin':'豊かさを拡散する人',
        'seizan_seizan':'財の達人','seizan_seikan':'現実的な成功者',
        'seizan_seiin':'賢い財運の持ち主','seikan_hikken':'戦略家',
        'seikan_shokusin':'突破力のある改革者','seikan_seizan':'実力で結果を出す人',
        'seikan_seikan':'強さと気概の人','seikan_seiin':'深謀遠慮のリーダー',
        'seiin_hikken':'自立した知識人','seiin_shokusin':'才能を深める探求者',
        'seiin_seizan':'知恵で稼ぐ人','seiin_seikan':'守護された知識人',
        'seiin_seiin':'深淵な精神の持ち主',
    }
    return names.get(f"{cat(day_star)}_{cat(month_star)}", '独自の才能タイプ')


def calc_all(birthdate_str, birth_time_str=''):
    """birthdate_str: 'YYYY-MM-DD', birth_time_str: 'HH:MM' or ''"""
    y, m, d = [int(x) for x in birthdate_str.split('-')]
    hour = 12.0
    if birth_time_str and ':' in birth_time_str:
        h, mn = birth_time_str.split(':')[:2]
        hour = int(h) + int(mn) / 60.0

    yp, _, _      = _year_pillar(y)
    mp, mk, ms    = _month_pillar(y, m)
    dp, dk, ds    = _day_pillar(y, m, d)

    month_shi_char = SHIS[ms]
    day_shi_char   = SHIS[ds]

    day_zok   = ZOKKAN[day_shi_char]
    month_zok = ZOKKAN[month_shi_char]

    day_main_star     = _tsuhen(dk, day_zok)
    month_center_star = _tsuhen(dk, month_zok)

    day_juunun   = _juunun(dk, day_shi_char)
    month_juunun = _juunun(dk, month_shi_char)

    de = JUENERGY.get(day_juunun, 5)
    me = JUENERGY.get(month_juunun, 5)
    energy_pct = int((de + me) / 24 * 100)

    composite_type = _composite(day_main_star, month_center_star)
    sun_sign  = _sun_sign(y, m, d)
    moon_sign = _moon_sign(y, m, d, hour)

    return {
        'year_pillar':       yp,
        'month_pillar':      mp,
        'day_pillar':        dp,
        'day_main_star':     day_main_star,
        'month_center_star': month_center_star,
        'day_juunun':        day_juunun,
        'month_juunun':      month_juunun,
        'energy_pct':        str(energy_pct),
        'composite_type':    composite_type,
        'sun_sign':          sun_sign,
        'moon_sign':         moon_sign,
        'asc':               '',
        'mc':                '',
    }


# ── Stripe ──
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')

PLAN_AMOUNTS = {'standard': 8000, 'light': 6000}
PLAN_NAMES   = {'standard': 'Standard プラン（完全鑑定レポート）',
                'light':    'Light プラン（完全鑑定レポート）'}
SUCCESS_URL  = 'https://uzumaki61876810-hub.github.io/goddess-diagnosis/fortune-diagnosis.html?payment=success'
CANCEL_URL   = 'https://uzumaki61876810-hub.github.io/goddess-diagnosis/apply-lp.html'
ALLOWED_ORIGIN = 'https://uzumaki61876810-hub.github.io'


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
        except Exception as e:
            self._respond(400, {'error': f'Invalid JSON: {e}'})
            return

        name        = str(data.get('name', '')).strip()
        email       = str(data.get('email', '')).strip()
        birthdate   = str(data.get('birthdate', '')).strip()
        birth_time  = str(data.get('birth_time', '')).strip()
        birth_place = str(data.get('birth_place', '')).strip()
        concern     = str(data.get('concern', 'income')).strip()
        plan        = str(data.get('plan', 'standard')).strip()

        if plan not in PLAN_AMOUNTS:
            self._respond(400, {'error': 'Invalid plan'})
            return
        if not birthdate:
            self._respond(400, {'error': 'birthdate required'})
            return

        # 四柱推命 / 占星術計算
        try:
            calc = calc_all(birthdate, birth_time)
        except Exception as e:
            calc = {'year_pillar':'','month_pillar':'','day_pillar':'',
                    'day_main_star':'','month_center_star':'',
                    'day_juunun':'','month_juunun':'','energy_pct':'75',
                    'composite_type':'','sun_sign':'','moon_sign':'','asc':'','mc':''}

        metadata = {
            'name':              name,
            'birthdate':         birthdate,
            'birth_time':        birth_time,
            'birth_place':       birth_place,
            'concern':           concern,
            'plan':              plan,
            'year_pillar':       calc['year_pillar'],
            'month_pillar':      calc['month_pillar'],
            'day_pillar':        calc['day_pillar'],
            'day_main_star':     calc['day_main_star'],
            'month_center_star': calc['month_center_star'],
            'day_juunun':        calc['day_juunun'],
            'month_juunun':      calc['month_juunun'],
            'energy_pct':        calc['energy_pct'],
            'composite_type':    calc['composite_type'],
            'sun_sign':          calc['sun_sign'],
            'moon_sign':         calc['moon_sign'],
            'asc':               calc['asc'],
            'mc':                calc['mc'],
        }

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'jpy',
                        'product_data': {'name': PLAN_NAMES[plan]},
                        'unit_amount': PLAN_AMOUNTS[plan],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                customer_email=email or None,
                metadata=metadata,
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
            )
            self._respond(200, {'url': session.url})
        except Exception as e:
            self._respond(500, {'error': str(e)})

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', ALLOWED_ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _respond(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass
