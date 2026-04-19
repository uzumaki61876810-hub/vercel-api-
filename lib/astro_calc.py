"""
天文計算モジュール
- 大運計算（節気ベース）
- ドラゴンヘッド/テイル（星座）
- 歳運（流年）
"""
import math
from datetime import date, datetime

KANS = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
SHIS = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
SIGNS = ['牡羊座','牡牛座','双子座','蟹座','獅子座','乙女座',
         '天秤座','蠍座','射手座','山羊座','水瓶座','魚座']

# ── ユリウス通日 ──
def to_jd(year, month, day, hour=12.0):
    if month <= 2:
        year -= 1; month += 12
    A = year // 100
    B = 2 - A + A // 4
    return int(365.25*(year+4716)) + int(30.6001*(month+1)) + day + B - 1524.5 + hour/24

# ── 節気計算（太陽黄経が30°の倍数になる日時）──
def solar_longitude(jd):
    """太陽黄経を返す（度）"""
    T = (jd - 2451545.0) / 36525
    L0 = 280.46646 + 36000.76983*T + 0.0003032*T*T
    M  = 357.52911 + 35999.05029*T - 0.0001537*T*T
    M  = math.radians(M % 360)
    C  = (1.914602 - 0.004817*T - 0.000014*T*T)*math.sin(M)
    C += (0.019993 - 0.000101*T)*math.sin(2*M)
    C += 0.000289*math.sin(3*M)
    sun_lon = (L0 + C) % 360
    # 黄道傾斜補正
    omega = 125.04 - 1934.136*T
    sun_lon -= 0.00569 - 0.00478*math.sin(math.radians(omega))
    return sun_lon % 360

def find_solar_term(year, month, target_lon):
    """指定した太陽黄経になる日時（JD）を二分法で求める"""
    # 概算開始JD
    jd = to_jd(year, month, 1)
    for _ in range(50):
        lon = solar_longitude(jd)
        diff = (target_lon - lon + 360) % 360
        if diff > 180: diff -= 360
        if abs(diff) < 0.0001:
            break
        jd += diff * (365.25/360)
    return jd

# 節（各月の入り：奇数黄経 15,45,75...）
# 各月の「節」の太陽黄経
# 節気の太陽黄経（各節気が発生する黄経）
# 月柱の切り替わりは「節」で決まる
# 例: 寒露(195°)≈10/8, 立冬(225°)≈11/7 ...
SETSU_LONS = {
    1: 285,   # 小寒  (1月上旬)
    2: 315,   # 立春  (2月上旬)
    3: 345,   # 啓蟄  (3月上旬)
    4: 15,    # 清明  (4月上旬)
    5: 45,    # 立夏  (5月上旬)
    6: 75,    # 芒種  (6月上旬)
    7: 105,   # 小暑  (7月上旬)
    8: 135,   # 立秋  (8月上旬)
    9: 165,   # 白露  (9月上旬)
    10: 195,  # 寒露  (10月上旬)
    11: 225,  # 立冬  (11月上旬)
    12: 255,  # 大雪  (12月上旬)
}

def get_setsu_jd(year, month):
    """指定年月の節入りJDを返す"""
    lon = SETSU_LONS[month]
    return find_solar_term(year, month, lon)

# ── 大運計算 ──
def calc_daun(birth_year, birth_month, birth_day, birth_hour, gender,
              month_kan_idx, month_shi_idx):
    """
    大運を計算して返す
    Returns: (start_age_float, list of (age, kan_shi_str))
    """
    # 年干の陰陽
    year_kan_idx = ((birth_year - 4) % 10 + 10) % 10
    is_yang_year = (year_kan_idx % 2 == 0)  # 陽干年=True

    # 順行 or 逆行
    # 陽干年・男 → 順行、陽干年・女 → 逆行
    # 陰干年・男 → 逆行、陰干年・女 → 順行
    is_forward = (is_yang_year and gender == 'M') or (not is_yang_year and gender == 'F')

    birth_jd = to_jd(birth_year, birth_month, birth_day, birth_hour)

    if is_forward:
        # 次の節を探す（同月の節より後なら翌月の節）
        setsu_jd = get_setsu_jd(birth_year, birth_month)
        if setsu_jd <= birth_jd:
            nm = birth_month + 1 if birth_month < 12 else 1
            ny = birth_year if birth_month < 12 else birth_year + 1
            setsu_jd = get_setsu_jd(ny, nm)
        days = setsu_jd - birth_jd
    else:
        # 直前の節を探す（当月の節が誕生日より後なら前月の節）
        setsu_jd = get_setsu_jd(birth_year, birth_month)
        if setsu_jd >= birth_jd:
            # 当月の節が誕生日より後 → 前月の節を使う
            pm = birth_month - 1 if birth_month > 1 else 12
            py = birth_year if birth_month > 1 else birth_year - 1
            setsu_jd = get_setsu_jd(py, pm)
        days = birth_jd - setsu_jd

    # 3日=1年、1日=4ヶ月
    start_age = days / 3.0
    # 端数は切り上げ（流派差を吸収するため）
    start_age_years  = math.ceil(start_age) if (start_age - int(start_age)) > 0.5 else int(start_age)
    start_age_months = round((start_age - int(start_age)) * 12)

    # 干支リスト生成
    daun_list = []
    for i in range(1, 9):
        if is_forward:
            ki = (month_kan_idx + i) % 10
            si = (month_shi_idx + i) % 12
        else:
            ki = ((month_kan_idx - i) % 10 + 10) % 10
            si = ((month_shi_idx - i) % 12 + 12) % 12
        age_start = start_age_years + (i-1)*10
        daun_list.append((age_start, KANS[ki]+SHIS[si]))

    return start_age_years, start_age_months, daun_list

# ── 歳運（流年）計算 ──
def calc_saiu(target_year):
    """指定年の歳運干支を返す"""
    ki = ((target_year - 4) % 10 + 10) % 10
    si = ((target_year - 4) % 12 + 12) % 12
    return KANS[ki] + SHIS[si]

def get_saiu_list(birth_year, count=10):
    """現在から count 年分の歳運リストを返す"""
    current_year = date.today().year
    return [(y, calc_saiu(y)) for y in range(current_year, current_year+count)]

# ── ドラゴンヘッド/テイル ──
def calc_dragon_head(year, month, day, hour_jst=12.0):
    """ドラゴンヘッドの黄経と星座を返す（True Node）
    hour_jstはJST（日本標準時）で渡すこと
    """
    hour_utc = hour_jst - 9  # JSTをUTCに変換
    jd = to_jd(year, month, day, hour_utc)
    T = (jd - 2451545.0) / 36525

    def rad(x): return math.radians(x % 360)

    # Mean Node (Omega)
    Omega = (125.04455501
             - 1934.136261 * T
             + 0.0020754   * T*T
             + T*T*T/467441) % 360

    # True Node補正項（Meeus Astronomical Algorithms）
    Mp = (134.96298 + 477198.867398*T + 0.0086972*T*T) % 360
    M  = (357.52911 + 35999.05029*T  - 0.0001537*T*T) % 360
    F  = (93.27191  + 483202.017538*T - 0.0036825*T*T) % 360
    D  = (297.85036 + 445267.111480*T - 0.0019142*T*T) % 360

    dOmega = (
        -1.4979 * math.sin(rad(2*(F-Omega)))
        -0.1500 * math.sin(rad(M))
        -0.1226 * math.sin(rad(2*F))
        +0.1176 * math.sin(rad(2*(F-Omega)))
        -0.0801 * math.sin(rad(2*(Mp-F)))
        +0.0364 * math.sin(rad(2*Omega))
        -0.0215 * math.sin(rad(2*(F-Omega)+M))
        +0.0155 * math.sin(rad(2*(F-Omega)-M))
        +0.0085 * math.sin(rad(2*(F-D)))
        -0.0061 * math.sin(rad(2*D))
    )

    true_node = (Omega + dOmega) % 360
    if true_node < 0: true_node += 360

    tail_lon = (true_node + 180) % 360
    return {
        'head_lon':  true_node,
        'head_sign': SIGNS[int(true_node/30)],
        'head_deg':  round(true_node % 30, 2),
        'tail_lon':  tail_lon,
        'tail_sign': SIGNS[int(tail_lon/30)],
        'tail_deg':  round(tail_lon % 30, 2),
    }

# ── ドラゴンヘッド/テイルの金運解釈 ──
DRAGON_INTERPRETATIONS = {
    '牡羊座': {
        'tail': '持って生まれた才能は「即断即決・開拓・自己主張」。前世から積み上げた行動力と独立心が魂に刻まれています。',
        'head': '今世の目標は「協調・パートナーシップ・他者との共存」。独りで突き進む才能を、人と調和させることで真の力が開花します。'
    },
    '牡牛座': {
        'tail': '持って生まれた才能は「物質的安定・蓄積・感覚の豊かさ」。前世からの財を守る力と審美眼が備わっています。',
        'head': '今世の目標は「変革・手放し・魂の深化」。執着を手放し、目に見えない力を信頼することで次のステージへ進めます。'
    },
    '双子座': {
        'tail': '持って生まれた才能は「知識・情報処理・コミュニケーション」。前世からの学習能力と言語センスが魂に宿っています。',
        'head': '今世の目標は「直感・大局観・精神的な深み」。知識を超えた叡智と信仰に向かうことで、魂の本来の目的が果たせます。'
    },
    '蟹座': {
        'tail': '持って生まれた才能は「養育・感情・家族への愛着」。前世からの共感力と人を守る力が魂に染み込んでいます。',
        'head': '今世の目標は「社会的達成・自立・キャリアの確立」。感情に流されず、社会に打って出ることで真の充足感を得られます。'
    },
    '獅子座': {
        'tail': '持って生まれた才能は「創造性・自己表現・舞台の中心」。前世からの輝きと存在感が魂に刻まれています。',
        'head': '今世の目標は「コミュニティ・友情・集合意識」。個人の輝きをグループの力に変換することで使命が果たされます。'
    },
    '乙女座': {
        'tail': '持って生まれた才能は「分析・細部へのこだわり・完璧な奉仕」。前世からの技術力と識別力が魂に宿っています。',
        'head': '今世の目標は「直感・癒し・大きな流れへの信頼」。分析で解決できない領域に身を委ねることで魂が解放されます。'
    },
    '天秤座': {
        'tail': '持って生まれた才能は「外交・バランス・美への感性」。前世からの調和を作る力と公平な判断力が備わっています。',
        'head': '今世の目標は「自己確立・個人の使命・独立した意思」。他者の評価より自分の軸を持つことで真の力が生まれます。'
    },
    '蠍座': {
        'tail': '持って生まれた才能は「変容・深層心理・隠れた力」。前世からの洞察力と再生の力が魂に刻まれています。',
        'head': '今世の目標は「単純化・誠実さ・地に足のついた豊かさ」。複雑さを手放し、シンプルに楽しむことで充足感が生まれます。'
    },
    '射手座': {
        'tail': '持って生まれた才能は「哲学・冒険・大局的な視点」。前世からの自由への渇望と真理を求める魂が宿っています。',
        'head': '今世の目標は「細部への集中・技術の習得・現実的な奉仕」。大きな理想を具体的な行動に落とし込むことが使命です。'
    },
    '山羊座': {
        'tail': '持って生まれた才能は「責任・組織構築・長期的戦略」。前世からの忍耐力と社会での地位を確立する力が備わっています。',
        'head': '今世の目標は「感情・直感・魂のルーツへの回帰」。効率や成果より、心の声に従うことで本来の豊かさが訪れます。'
    },
    '水瓶座': {
        'tail': '持って生まれた才能は「革新・独自性・集合知」。前世からの社会変革への意志と先見性が魂に刻まれています。',
        'head': '今世の目標は「個人の創造性・自己表現・純粋な喜び」。集団より自分の内なる輝きを信じることで才能が解放されます。'
    },
    '魚座': {
        'tail': '持って生まれた才能は「直感・癒し・霊的な感受性」。前世からの深い共感力とスピリチュアルな知恵が魂に宿っています。',
        'head': '今世の目標は「現実的な分析・技術の習得・識別力」。感覚だけでなく、論理と技術を身につけることで才能が現実化します。'
    },
}

def get_dragon_interpretation(head_sign, tail_sign):
    head_interp = DRAGON_INTERPRETATIONS.get(head_sign, {})
    tail_interp = DRAGON_INTERPRETATIONS.get(tail_sign, {})
    return {
        'tail_text': tail_interp.get('tail', ''),
        'head_text': head_interp.get('head', ''),
    }

# ── テスト実行 ──
if __name__ == '__main__':
    print('=== 晶子さんの計算テスト ===')
    print()

    # 大運
    s_y, s_m, daun = calc_daun(
        1970, 10, 6, 10.43, 'F',
        month_kan_idx=1,  # 乙
        month_shi_idx=9,  # 酉
    )
    print(f'大運開始: {s_y}歳{s_m}ヶ月')
    print('大運一覧:')
    for age, ks in daun:
        print(f'  {age}歳〜{age+9}歳: {ks}')
    print()

    # 歳運
    print('歳運（今後10年）:')
    for year, ks in get_saiu_list(1970):
        print(f'  {year}年: {ks}')
    print()

    # ドラゴンヘッド
    dh = calc_dragon_head(1970, 10, 6, 1.43)
    print(f'ドラゴンヘッド: {dh["head_sign"]} {dh["head_deg"]}°')
    print(f'ドラゴンテイル: {dh["tail_sign"]} {dh["tail_deg"]}°')
    interp = get_dragon_interpretation(dh['head_sign'], dh['tail_sign'])
    print()
    print('テイル解釈:', interp['tail_text'])
    print()
    print('ヘッド解釈:', interp['head_text'])
