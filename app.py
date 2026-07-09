import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import re
import json

# ────────────────────────────────────────────────────────────
# 1. 앱 메타데이터 및 UI 디자인 시스템 주입
#    모토: 토스처럼 동글동글하되, 금융 앱다운 세미포멀함과 접근성을 함께
# ────────────────────────────────────────────────────────────
st.set_page_config(page_title="시니어 안심 금융가드 AI", page_icon="🛡️", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/web/CSS/suit-no-vf.css');

    :root {
        /* 배경/서페이스 - aliceblue 계열의 부드러운 하늘색 그러데이션 */
        --c-bg:#F0F8FF;
        --c-surface:#FFFFFF;
        --c-border:#C9DBF0;
        --c-border-strong:#BFDBFB;
        /* 강조색 - royalblue(주요 액션) / dodgerblue(링크·아이콘) */
        --c-primary:#4169E1;
        --c-primary-tint:#EAF3FE;
        --c-primary-dark:#2748AE;
        --c-link:#1E90FF;
        /* 텍스트 - 진한 남색 계열로 은행 앱다운 대비감 */
        --c-text:#101A33;
        --c-text-secondary:#51607A;
        --c-text-muted:#8A96AC;
        /* 위험도 신호 - 실제 사기 경보의 즉각적인 인지를 위해 적/황/녹은 유지 */
        --c-danger:#E53E3E;
        --c-danger-tint:#FFF1F0;
        --c-warning:#D48806;
        --c-warning-tint:#FFFBE6;
        --c-success:#2E7D32;
        --c-success-tint:#E7F5E9;
        --radius-lg:20px;
        --radius-md:14px;
        --radius-sm:10px;
    }

    html, body, [class*="css"], * {
        font-family: 'SUIT', -apple-system, BlinkMacSystemFont, sans-serif !important;
        letter-spacing: -0.3px;
    }
    /* Streamlit 내부 아이콘(사이드바 접기 화살표 등)은 전용 아이콘 폰트를 써야 하므로
       위의 전체 폰트 강제 지정에서 제외합니다. 이걸 빼먹으면 아이콘이 "keyboard_double_arrow_right"
       같은 글자 그대로 깨져 보입니다. */
    [data-testid="stIconMaterial"],
    span[class*="material-symbols"],
    span[class*="material-icons"],
    i[class*="material-icons"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        letter-spacing: normal !important;
    }
    [data-testid="stAppViewContainer"], body, .main {
        background: linear-gradient(180deg, #FFFFFF 0%, #F0F8FF 45%, #E6F1FB 100%) !important;
    }
    p, span, div, label { color: var(--c-text); }

    /* ======== [고정 1] 탭: 선택 시 뜨는 빨간 인디케이터 완전 제거 ========
       BaseWeb 탭은 버전에 따라 highlight/border 두 요소로 빨간 줄을 그리거나,
       선택된 탭 버튼 자체의 border-bottom으로 그리기도 해서 두 경로 모두 차단합니다. */
    div[data-baseweb="tab-highlight"],
    div[data-baseweb="tab-border"] {
        display: none !important;
        background-color: transparent !important;
        height: 0 !important;
    }
    button[data-baseweb="tab"]::before,
    button[data-baseweb="tab"]::after,
    div[data-baseweb="tab-list"]::before,
    div[data-baseweb="tab-list"]::after {
        display: none !important;
    }
    [data-testid="stTabs"] { border-bottom: none !important; }
    div[data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: none !important;
        padding: 6px 0 14px 0;
    }
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 12px !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        min-width: 116px;
        padding: 12px 16px !important;
        color: var(--c-text-secondary) !important;
        font-weight: 600 !important;
        transition: all 0.15s ease;
    }
    button[data-baseweb="tab"]:hover {
        background-color: var(--c-primary-tint) !important;
        color: var(--c-primary) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--c-primary-tint) !important;
        border: 1px solid var(--c-border-strong) !important;
        box-shadow: none !important;
        color: var(--c-primary) !important;
        font-weight: 700 !important;
    }

    /* ======== [고정 3] 공통 필드 라벨: 위젯 기본 라벨 대신 동일 스타일로 직접 렌더링 ======== */
    .field-label {
        font-size: 15px;
        font-weight: 700;
        color: var(--c-text);
        margin: 0 0 8px 0;
        letter-spacing: -0.3px;
    }

    /* ======== [고정 2] 사진 업로드 존: 한국어 안내 + 버튼 라벨 정리 ======== */
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploadDropzone"] {
        background-color: var(--c-surface) !important;
        border: 1.5px dashed #B7CBEA !important;
        border-radius: var(--radius-md) !important;
        padding: 28px 16px !important;
        min-height: 132px;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 12px !important;
        position: relative;
    }
    /* 기본 영문 안내(아이콘+"Drag and drop..."+"Limit 200MB...")는 통째로 숨기고,
       드롭존 자체의 ::before/::after로 한글 문구를 새로 그립니다 - 내부 DOM 구조가
       버전마다 달라도 겹쳐 보이는 문제 없이 안정적으로 동작합니다. */
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploaderDropzone"]::before,
    [data-testid="stFileUploadDropzone"]::before {
        content: "사진을 끌어다 놓거나, 아래 버튼으로 선택하세요";
        order: -1;
        font-size: 14.5px; font-weight: 600; color: var(--c-text-secondary);
        text-align: center;
    }
    [data-testid="stFileUploaderDropzone"]::after,
    [data-testid="stFileUploadDropzone"]::after {
        content: "PNG, JPG 파일 · 최대 200MB";
        order: 2;
        font-size: 12.5px; color: var(--c-text-muted);
    }
    [data-testid="stFileUploaderDropzone"] button,
    [data-testid="stFileUploadDropzone"] button {
        font-size: 0 !important;
        color: transparent !important;
        background-color: #FFFFFF !important;
        border: 1.5px solid #A9C3ED !important;
        border-radius: var(--radius-sm) !important;
        position: relative;
        width: 112px;
        height: 40px;
        order: 0;
    }
    /* 버튼 안쪽에 남아있을 수 있는 모든 텍스트/아이콘을 크기 0으로 만들어
       "uploadUpload"처럼 겹쳐 보이는 잔여 텍스트를 원천 차단합니다. */
    [data-testid="stFileUploaderDropzone"] button *,
    [data-testid="stFileUploadDropzone"] button * {
        font-size: 0 !important;
        color: transparent !important;
    }
    [data-testid="stFileUploaderDropzone"] button svg,
    [data-testid="stFileUploadDropzone"] button svg { display: none !important; }
    [data-testid="stFileUploaderDropzone"] button::after,
    [data-testid="stFileUploadDropzone"] button::after {
        content: "업로드";
        color: var(--c-primary) !important;
        font-weight: 700;
        font-size: 14px !important;
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
    }
    [data-testid="stFileUploaderFile"] {
        background-color: #F9FAFB !important;
        border: 1px solid var(--c-border) !important;
        border-radius: var(--radius-sm) !important;
        padding: 6px 12px !important;
        margin-top: 8px !important;
    }

    /* ======== 입력 카드를 감싸는 컨테이너 (st.container(border=True)) ======== */
    [data-testid="stVerticalBlockBorderWrapper"] > div,
    div[data-testid="stContainer"] {
        background-color: var(--c-surface) !important;
        border: 1px solid var(--c-border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 20px !important;
        box-shadow: 0 1px 3px rgba(16,26,51,0.05), 0 6px 20px rgba(16,26,51,0.04) !important;
    }

    /* ======== 버튼 ======== */
    .stButton > button {
        background-color: var(--c-surface);
        color: var(--c-text);
        border: 1px solid var(--c-border);
        border-radius: var(--radius-md);
        padding: 18px 22px;
        font-size: 16px; font-weight: 600;
        width: 100%; height: auto;
        text-align: left;
        box-shadow: none;
        transition: all 0.15s ease;
    }
    .stButton > button p { text-align: left !important; width: 100%; margin: 0; font-size: 16px; }
    .stButton > button:hover {
        background-color: var(--c-primary-tint) !important;
        color: var(--c-primary) !important;
        border-color: var(--c-border-strong) !important;
        transform: translateY(-1px);
    }
    .stButton > button:focus-visible {
        box-shadow: 0 0 0 3px var(--c-primary-tint) !important;
        border-color: var(--c-primary) !important;
    }

    button[kind="primary"] {
        background-color: var(--c-primary) !important;
        color: #FFFFFF !important;
        border-radius: var(--radius-md) !important;
        padding: 18px !important;
        border: none !important;
        box-shadow: 0 3px 10px rgba(65, 105, 225, 0.20) !important;
    }
    button[kind="primary"]:hover { background-color: var(--c-primary-dark) !important; }
    button[kind="primary"] p { text-align: center !important; font-weight: 700 !important; font-size: 17px; color: white !important; }

    /* ======== 카드 & 입력 ======== */
    .toss-card {
        background-color: var(--c-surface);
        padding: 24px;
        border-radius: var(--radius-lg);
        box-shadow: none;
        margin-bottom: 16px;
        border: 1px solid var(--c-border);
    }
    .trust-row {
        display: flex; align-items: center; flex-wrap: wrap;
        gap: 7px;
        font-size: 12.5px; color: var(--c-text-secondary);
        margin: 4px 0 22px 0;
    }
    .trust-row .dot { color: var(--c-border-strong); font-weight: 700; }
    .trust-row .item { display: inline-flex; align-items: center; gap: 5px; }
    .trust-row .item svg { color: var(--c-primary); flex-shrink: 0; }

    textarea {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--c-border) !important;
        background-color: var(--c-surface) !important;
        padding: 16px !important;
        font-size: 15.5px !important;
        line-height: 1.6 !important;
        color: var(--c-text) !important;
    }
    textarea::placeholder { color: var(--c-text-muted) !important; opacity: 1; }
    textarea:focus {
        border-color: var(--c-primary) !important;
        box-shadow: 0 0 0 3px var(--c-primary-tint) !important;
    }

    input[type="checkbox"] { accent-color: var(--c-primary); width: 18px; height: 18px; }

    /* ======== 배지 ======== */
    .badge { display: inline-block; padding: 5px 11px; border-radius: 8px; font-size: 12px; font-weight: 700; margin-bottom: 10px; }
    .badge-sky { background-color: var(--c-primary-tint); color: var(--c-primary); }
    .badge-red { background-color: var(--c-danger-tint); color: var(--c-danger); }
    .badge-amber { background-color: var(--c-warning-tint); color: var(--c-warning); }
    .badge-green { background-color: var(--c-success-tint); color: var(--c-success); }
    </style>
""", unsafe_allow_html=True)

# 3. 고도화된 정밀 시니어 사기 예방 지식 아카이브 (구조화 데이터셋)
fraud_db = {
    "01 검찰·금융감독원 사칭 협박": {
        "summary": "검찰·경찰·금융감독원 등 국가기관을 사칭하는 수법으로, 2025년 기준 전체 보이스피싱의 51%를 차지하는 가장 빈번한 유형입니다. (출처: 경찰청 국가수사본부, 2016년 대비 발생 건수 약 4배 증가)",
        "example": "“서울중앙지검 첨단범죄수사팀 김민수 검사입니다. 귀하 명의의 대포통장이 개설되어 범죄 자금 세탁에 악용되었습니다. 협조하지 않으면 구속 수사합니다.”",
        "mechanism": "공문서와 신분증 위조 사진을 전송해 신뢰를 얻은 후, 자산의 결백성을 증명해야 한다며 금융감독원의 이른바 '안전보호계좌'로 전산을 통해 자금을 이체하라고 강요합니다. 실제 사용 중인 기관 전화번호를 약 80여 개나 미리 목록화해두고, 피해자가 검찰·경찰 대표번호로 직접 걸어도 사기 조직으로 연결되게 만드는 '강제수신·강제발신(강수강발)' 기능까지 악성 앱에 심어두는 경우도 있습니다.",
        "counter": "1. 검찰, 경찰, 금융감독원 등 수사·정부 기관은 절대로 전화나 문자로 자금을 요구하거나 안전 계좌로 이체를 요구하지 않습니다.\n2. 당황하지 마시고 전화를 즉시 끊은 뒤, 포털에서 다시 검색한 공식 대표번호(검찰 1301, 경찰 112)로 직접 전화해 확인하세요.\n3. 영장이나 공문서를 스마트폰 메시지로 보내는 수사기관은 세상에 없습니다.\n4. '사건조회', '특급보안·엠바고', '약식조사·보호관찰', '자산검수·자산이전' 같은 표현은 경찰청이 공식 지정한 사기 위험 신호이니, 들리는 즉시 전화를 끊으세요."
    },
    "02 메신저 피싱 (가족 사칭)": {
        "summary": "자녀·조카의 프로필을 교묘하게 베껴 카카오톡으로 접근한 뒤 돈이나 정보를 가로챕니다. 보이스피싱 피해자 중 50대 이상 비중이 2023년 32%에서 2025년 53%까지 늘며, 특히 중장년층을 노리는 대표적인 수법입니다. (출처: 경찰청 국가수사본부)",
        "example": "“엄마 나 지수인데 핸드폰 액정이 깨져서 수리 맡겼어. 통화 안 되니까 여기 링크 눌러서 인증서 좀 대신 받아줘.”",
        "mechanism": "통화 불가를 핑계로 부모의 심리적 불안을 자극하며, 악성 원격제어 앱 설치를 유도해 스마트폰 안의 은행 앱을 마음대로 조작합니다.",
        "counter": "1. 아무리 다급해도 메시지 대화만으로는 절대 돈을 보내거나 민감한 정보를 주지 마세요.\n2. 반드시 기존에 저장된 자녀의 전화번호로 직접 전화를 걸어 실제 상황인지 목소리를 확인하세요.\n3. 링크가 포함된 문자나 카톡은 절대 누르면 안 됩니다."
    },
    "03 정부 지원금 빙자 스미싱": {
        "summary": "서민금융진흥원이나 대형 시중은행을 사칭하여 저금리 정부 대출을 해준다고 유혹합니다.",
        "example": "“[국민복지지원] 코로나 상생 소비지원금 및 민생안정특별대출 신청 안내. 기한 내 미신청 시 자동 소멸. 신청 링크: bit.ly/sh-bank”",
        "mechanism": "공신력 있는 기관의 이름을 악용해 정책 자금 신청 기한이 임박한 것처럼 속여 가짜 금융 앱(.apk) 설치를 유도해 개인 정보를 가로챕니다.",
        "counter": "1. 시중 은행과 정부 기관은 절대로 문자 메시지를 통해 대출 광고나 신청 링크를 먼저 발송하지 않습니다.\n2. 출처가 불분명한 단축 URL은 절대 클릭하지 마시고 메시지를 즉시 삭제하세요.\n3. 의심스러울 때는 해당 금융회사의 공식 대표번호로 직접 전화해 사실 여부를 조회하십시오."
    },
    "04 금융기관 사칭 대환대출 사기": {
        "summary": "고금리 대출로 힘들어하는 취약계층에게 연 2~3%대 저금리로 갈아타게 해주겠다며 접근합니다.",
        "example": "“[SH신한] 정부 주도 서민 맞춤형 대환대출 특별 조치 안내. 기존 고금리 대출을 최저 연 2.8%로 즉시 전환 가능. 당일 한도 마감 직전.”",
        "mechanism": "신용등급을 올려야 한다거나 대출 조건 충족을 위해 기존 대출금을 우선 상환하라고 압박하며 사기단이 지정한 개인 계좌(대포통장)로 송금을 유도합니다.",
        "counter": "1. 전화나 문자로 먼저 대환대출을 권유하며 '기존 대출금을 즉시 상환하라'고 요구하는 행위는 100% 사기입니다.\n2. 금융회사는 어떠한 경우에도 대출 상환금을 직원의 개인 계좌나 현금으로 직접 수거하지 않습니다.\n3. 금융감독원 파인(FINE) 홈페이지에서 제도권 금융회사인지 반드시 검증하십시오."
    },
    "05 주식 리딩방 및 고수익 투자 사기": {
        "summary": "노후 자금 마련이 시급한 은퇴 계층의 심리를 저격하여 원금 보장과 고수익을 미끼로 유혹합니다.",
        "example": "“[VIP 주식방 정보] 상장 임박 비상장 주식 비공개 물량 독점 확보. 선착순 50명 원금 100% 보장 및 하루 수익 300% 달성 보장 수익방 입장”",
        "mechanism": "가짜 주식 거래 프로그램(HTS) 화면을 조작해 매일 엄청난 수익이 나는 것처럼 가짜 시각 자료를 보여준 뒤, 투자금을 입금하면 사이트를 폐쇄하고 잠적합니다.",
        "counter": "1. 고수익이 나면서 원금까지 완벽히 보장되는 합법적 투자 상품은 이 세상에 결코 존재하지 않습니다.\n2. 제도권 증권 회사가 아닌 사설 투자방이나 리딩방에서 유도하는 개인 계좌 이체는 절대 거부하세요.\n3. 금융 투자 전 반드시 금융감독원에 정식 등록된 투자 자문 업체인지 확인해야 안전합니다."
    },
    "06 택배 미배달 주소지 확인 스미싱": {
        "summary": "명절, 연말연시 등 물량이 몰리는 시기를 틈타 주소지나 통관 문제 조정을 핑계로 낚아챕니다.",
        "example": "“[CJ대한통운] 고객님 물품이 주소지 미확인으로 배송 지연 중입니다. 아래 주소 확인 후 수정 바랍니다. 주소변경주소: cj-ko.info”",
        "mechanism": "누구나 일상적으로 이용하는 택배 서비스를 빙자해 링크 클릭을 유도하며, 링크를 누르는 순간 스마트폰에 소액결제 악성코드가 심어집니다.",
        "counter": "1. 택배사에서는 주소지가 잘못되었을 때 개인 휴대폰 문자 링크로 주소 수정을 요구하지 않습니다.\n2. 송장 번호 조회는 공식 택배사 홈페이지나 앱을 통해서만 조회를 진행하세요.\n3. 문자 수신 즉시 해당 번호를 차단 처리하는 것이 안전합니다."
    },
    "07 해외 부정결제 알림 사기": {
        "summary": "사용하지도 않은 거액의 해외 결제 문자를 보내 당황한 피해자가 전화를 걸게 만듭니다.",
        "example": "“[해외인증결제] Amazon인증 미화 $899 결제 완료. 본인 발급 아닐 시 가짜 소비자센터 접수: 02-1588-XXXX”",
        "mechanism": "해킹이나 명의 도용 범죄에 휘말렸다는 공포심을 자극해 문자에 기재된 가짜 고객센터로 전화를 유도한 뒤, 보안 강화를 명목으로 자금을 송금하게 합니다.",
        "counter": "1. 수신된 문자에 적힌 전화번호는 사기단의 대포폰이므로 절대로 그 번호로 전화를 걸면 안 됩니다.\n2. 본인이 사용하는 신용카드사에 직접 전화를 걸거나 카드사 공식 앱을 켜서 실제 승인 내역이 있는지 확인하세요.\n3. 금전적 피해가 우려되면 카드 승인 거절 조치를 즉시 신청하세요."
    },
    "08 청첩장 및 부고장 위장 피싱": {
        "summary": "지인의 경조사를 챙기는 한국인의 미덕과 따뜻한 정을 악독하게 악용하는 생활 침투형 범죄입니다.",
        "example": "“모시는 글: 저희 둘 하나 되어 새로운 출발을 합니다. 바쁘시더라도 참석해 자리를 빛내주세요. 모바일청첩장보기: wedding-inv.com”",
        "mechanism": "아는 사람의 이름으로 오기 때문에 아무런 의심 없이 링크를 누르게 되며, 좀비 스마트폰이 되어 내 연락처의 모든 사람에게 동일한 사기 문자를 자동 대량 발송합니다.",
        "counter": "1. 모르는 번호로 온 경조사 문자는 물론, 지인의 번호로 왔더라도 문맥이 어색하면 절대 링크를 누르지 마세요.\n2. 메신저나 전화를 통해 상대방에게 실제로 보낸 청첩장/부고장이 맞는지 직접 육성 통화로 재확인하십시오.\n3. 스마트폰 보안 설정에서 '출처를 알 수 없는 앱 설치 제한'을 반드시 활성화해 두세요."
    }
}

# 4. AI 응답 텍스트 정리 유틸
#    Gemini가 자체적으로 넣는 마크다운 **볼드** 표기가 raw HTML 블록 안에서는
#    별표 그대로 노출되는 경우가 있어 직접 <strong> 태그로 바꿔주고,
#    "...다. 2. ..." 처럼 붙어버린 번호 매김 사이에 줄바꿈을 넣어 가독성을 높입니다.
def _to_html(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'([.\)"\u201d\u2019])\s+(\d+)\.\s+', r'\1<br><br>\2. ', text)
    text = text.replace('\n', '<br>')
    return text

def _to_plain(text: str) -> str:
    """카카오톡 등에 그대로 붙여넣기 좋은 순수 텍스트(마크업 없음) 버전"""
    text = (text or "").strip()
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'([.\)"\u201d\u2019])\s+(\d+)\.\s+', r'\1\n\n\2. ', text)
    return text

# 5. 정밀 다이얼로그 팝업 빌더 (콘텐츠 깊이 전면 보강)
@st.dialog("🛡️ 정밀 분석 결과 및 안전 대처 수칙")
def show_detail_guide(title, data_dict):
    st.markdown(f"<span class='badge badge-sky'>금융감독원 공식 매뉴얼 연계</span>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:var(--c-primary); font-weight:800; margin-top:0; margin-bottom:12px;'>{title}</h3>", unsafe_allow_html=True)

    st.markdown("""<p style='font-size:14px; font-weight:700; color:var(--c-text-secondary); margin-bottom:4px;'>📌 수법 한줄 요약</p>""", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:16px; font-weight:500; line-height:1.6; color:var(--c-text); margin-bottom:18px;'>{data_dict['summary']}</p>", unsafe_allow_html=True)

    st.markdown("""<p style='font-size:14px; font-weight:700; color:var(--c-danger); margin-bottom:4px;'>💬 실제 범죄 문자/카톡 예시</p>""", unsafe_allow_html=True)
    st.markdown(f"<div style='background-color:var(--c-danger-tint); padding:16px; border-radius:12px; font-size:15px; font-weight:600; font-style:italic; color:#991B1B; line-height:1.6; margin-bottom:18px;'>{data_dict['example']}</div>", unsafe_allow_html=True)

    st.markdown("""<p style='font-size:14px; font-weight:700; color:var(--c-text-secondary); margin-bottom:4px;'>⚙️ 사기단의 범죄 메커니즘</p>""", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:15px; line-height:1.6; color:var(--c-text-secondary); margin-bottom:18px;'>{data_dict['mechanism']}</p>", unsafe_allow_html=True)

    st.markdown("<div style='height: 1px; background-color: var(--c-border); margin: 20px 0;'></div>", unsafe_allow_html=True)
    st.markdown("""<p style='font-size:15px; font-weight:800; color:var(--c-primary); margin-bottom:8px;'>🔒 부모님을 위한 3대 안심 방어 수칙</p>""", unsafe_allow_html=True)
    st.markdown(f"<div style='background-color:var(--c-primary-tint); padding:18px; border-radius:14px; font-size:15px; font-weight:600; line-height:1.7; color:#1A4998;'>{data_dict['counter'].replace(chr(10), '<br><br>')}</div>", unsafe_allow_html=True)

    st.write("")
    if st.button("내용을 확인했습니다", type="primary", use_container_width=True):
        st.rerun()

# 6. 긴급 전용 원터치 전화 신고 스크립트 팝업 빌더
@st.dialog("📞 긴급 전화를 걸기 전 읽어보세요")
def show_emergency_script(center_name, dial_num, script_text):
    st.markdown(f"<span class='badge badge-red'>골든타임 프로토콜</span>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:var(--c-danger); font-weight:800; margin-top:0;'>{center_name} ({dial_num}) 연결 안내</h3>", unsafe_allow_html=True)
    st.markdown("전화가 연결되면 당황하지 마시고 아래 문장을 **그대로** 상담원에게 읽어주세요.")

    st.markdown(f"""
        <div style="background-color:#F9FAFB; padding:20px; border-radius:14px; border:1px solid var(--c-border); margin:16px 0;">
            <p style="font-size:16px; font-weight:700; line-height:1.7; color:var(--c-text); margin:0; white-space:pre-line;">{script_text}</p>
        </div>
    """, unsafe_allow_html=True)
    st.info("💡 통화 도중 상담원이 원격 제어 프로그램 설치나 송금을 요구하는 경우는 절대 없으니 안심하고 접수하세요.")
    if st.button("확인 후 창 닫기", use_container_width=True):
        st.rerun()

# --- 메인 브랜드 헤더 ---
# 컬러 이모지 대신 브랜드 컬러(royalblue) 라인 아이콘을 직접 그려서 실제 금융 앱에 가까운
# 절제된 인상을 주도록 했습니다. (방패=서비스 마크, 자물쇠/번개/사람=신뢰 요소)
st.write("")
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:2px;">
  <div style="width:42px; height:42px; border-radius:13px; background-color:var(--c-primary); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 21s7.5-3.5 7.5-9.5V6l-7.5-3-7.5 3v5.5C4.5 17.5 12 21 12 21z"/>
      <path d="M9 12l2 2 4-4"/>
    </svg>
  </div>
  <h1 style="margin:0; font-size:23px; font-weight:800; color:var(--c-text); letter-spacing:-0.5px;">시니어 안심 금융가드 AI</h1>
</div>
<p style="font-size:14px; color:var(--c-text-secondary); margin:8px 0 4px 0; line-height:1.6;">어르신을 노리는 메신저·투자·정부지원금 사기를, AI가 미리 확인해 드려요.</p>
<div class="trust-row">
  <span class="item">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
    입력 내용 저장 안 함
  </span>
  <span class="dot">·</span>
  <span class="item">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
    몇 초면 결과 확인
  </span>
  <span class="dot">·</span>
  <span class="item">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
    가족과 결과 공유 가능
  </span>
</div>
""", unsafe_allow_html=True)

DEMO_LIMIT = 5  # 체험 모드에서 세션(브라우저 탭)당 허용하는 무료 사용 횟수

if "demo_uses" not in st.session_state:
    st.session_state.demo_uses = 0

with st.sidebar:
    st.markdown("#### 🔑 AI 분석 방식")
    key_mode = st.radio(
        "AI 분석 방식",
        ["체험 모드 (무료)", "내 API 키로 사용"],
        label_visibility="collapsed"
    )

    try:
        demo_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        demo_key = ""

    if key_mode == "내 API 키로 사용":
        api_key = st.text_input(
            "Google AI API 키",
            type="password",
            placeholder="AIza로 시작하는 키를 입력하세요",
            label_visibility="collapsed"
        )
        st.caption("입력하신 키와 대화 내용은 서버에 저장되지 않고, 실시간 분석에만 사용돼요.")
    else:
        api_key = demo_key
        remaining = max(DEMO_LIMIT - st.session_state.demo_uses, 0)
        if demo_key:
            st.caption(f"체험 모드는 세션당 {DEMO_LIMIT}회까지 무료로 사용할 수 있어요. (남은 횟수: {remaining}회)")
            st.caption("Google 무료 API를 사용하며, 입력 내용이 모델 개선에 활용될 수 있어요. 실제 계좌번호 등 민감정보는 가려주세요.")
        else:
            st.warning("데모 키가 아직 설정되지 않았어요. 배포 시 Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요.")

# --- 완전체 4대 토스 파생형 메인 탭 ---
tab1, tab2, tab3, tab4 = st.tabs(["실시간 진단", "최신 사기 Top 3", "유형별 대응법", "긴급 신고"])

# ----------------- TAB 1: 실시간 피싱 진단 -----------------
with tab1:
    st.write("")

    with st.container(border=True):
        st.markdown("""
        <div style="margin:-20px -20px 20px -20px; padding:15px 20px; border-bottom:1px solid var(--c-border); border-radius:19px 19px 0 0; background-color:#FFFFFF; display:flex; align-items:center;">
          <div style="display:flex; align-items:center; gap:8px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--c-primary)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7.5-3.5 7.5-9.5V6l-7.5-3-7.5 3v5.5C4.5 17.5 12 21 12 21z"/><path d="M9 12l2 2 4-4"/></svg>
            <span style="font-size:15px; font-weight:800; color:var(--c-text); letter-spacing:-0.3px;">AI 사기 탐지</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="field-label">수신된 의심 문장이나 카카오톡 대화 내용</p>', unsafe_allow_html=True)
        user_input = st.text_area(
            "수신된 의심 문장이나 카카오톡 대화 내용",
            placeholder="예) 엄마 나 수정인데 핸드폰 액정이 깨졌어.. 링크 눌러줘",
            height=140,
            label_visibility="collapsed"
        )

        st.markdown('<p class="field-label" style="margin-top:20px;">글자를 옮기기 어렵다면 캡처 화면(사진)을 넣어주세요</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "의심되는 문자나 카카오톡 캡처 이미지 업로드",
            type=['png', 'jpg', 'jpeg'],
            label_visibility="collapsed"
        )

        if uploaded_file:
            st.write("")
            st.image(uploaded_file, caption="분석 대기 중인 사진", width=140)

        st.write("")
        generate_card = st.checkbox("가족/지인 공유용 디지털 안전 경고장 자동 제작")

    st.write("")

    if st.button("금융 사기 여부 정밀 검사 시작", type="primary", use_container_width=True):
        if key_mode == "체험 모드 (무료)" and st.session_state.demo_uses >= DEMO_LIMIT:
            st.error(f"체험 모드 무료 횟수({DEMO_LIMIT}회)를 모두 사용하셨어요. 왼쪽 메뉴에서 '내 API 키로 사용'을 선택하면 계속 이용하실 수 있어요.")
        elif not api_key:
            st.error("⚠️ 안전 정밀 검사를 진행하려면 좌측 메뉴에서 API 키를 확인해 주세요.")
        elif not user_input and not uploaded_file:
            st.warning("⚠️ 검사할 텍스트 대화 내용을 입력하거나 사진 파일을 업로드해 주세요.")
        else:
            with st.spinner("🔒 금융 범죄 데이터베이스 및 이미지 텍스트 판독 엔진 분석 중..."):
                try:
                    client = genai.Client(api_key=api_key)
                    system_instruction = (
                        "너는 금융 사기 예방 권위자 AI야. 입력 데이터를 분석해 위험도를 판별해.\n"
                        "경찰청 국가수사본부가 공식 발표한 보이스피싱 위험 키워드(사건조회, 특급보안·엠바고, "
                        "약식조사·보호관찰, 자산검수·자산이전, 감상문 제출 등 실제 수사기관은 절대 요구하지 않는 표현)가 "
                        "포함되어 있는지 특히 주의 깊게 확인해.\n"
                        "결과는 반드시 아래의 포맷을 누락 없이 출력해줘.\n\n"
                        "[위험등급]: 위험, 주의, 안심 중 하나\n"
                        "[상황요약]: 노년층이 즉시 이해할 수 있는 한줄 요약\n"
                        "[의심정황]: 피싱이라고 판단되는 구체적 요인 기술\n"
                        "[대처지침]: 지금 당장 실행할 행동수칙"
                    )

                    content_inputs = []
                    if uploaded_file: content_inputs.append(Image.open(uploaded_file))
                    if user_input: content_inputs.append(user_input)
                    else: content_inputs.append("첨부 사진 속 금융 사기 정황을 정밀 해독하라.")

                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=content_inputs,
                        config=types.GenerateContentConfig(system_instruction=system_instruction)
                    )
                    res_raw = response.text

                    if key_mode == "체험 모드 (무료)":
                        st.session_state.demo_uses += 1

                    # [예외 제로 패치] 어떤 구분자 파괴 상황에서도 정확하게 데이터를 추출하는 예외 방어 정규식 파싱 기술 적용
                    grade_match = re.search(r'\[위험등급\]\s*:\s*(.*)', res_raw)
                    summary_match = re.search(r'\[상황요약\]\s*:\s*(.*)', res_raw)
                    reasons_match = re.search(r'\[의심정황\]\s*:\s*([\s\S]*?)(?=\[|$)', res_raw)
                    action_match = re.search(r'\[대처지침\]\s*:\s*([\s\S]*?)(?=\[|$)', res_raw)

                    grade = grade_match.group(1).strip() if grade_match else "위험"
                    summary_raw = summary_match.group(1).strip() if summary_match else "의심스러운 금융 사기 정황 감지"
                    reasons_raw = reasons_match.group(1).strip() if reasons_match else "출처 불명의 링크 및 자금 탈취 유도 패턴"
                    action_raw = action_match.group(1).strip() if action_match else "절대 송금하거나 링크를 누르지 마십시오."

                    # Gemini 응답에 섞인 **볼드** 표기를 실제 HTML로, 번호 매김 사이에 줄바꿈을 넣어 정리
                    summary = _to_html(summary_raw)
                    reasons = _to_html(reasons_raw)
                    action = _to_html(action_raw)

                    if "위험" in grade:
                        chip_bg, chip_border = "#000080", "#191970"
                        icon_bg, icon_color = "rgba(255,255,255,0.16)", "#FFFFFF"
                        text_color, sub_color = "#FFFFFF", "#B7C6EF"
                        chip_title, chip_sub = "위험", "사기 확률 매우 높음"
                        chip_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7.5-3.5 7.5-9.5V6l-7.5-3-7.5 3v5.5C4.5 17.5 12 21 12 21z"/><line x1="9.5" y1="9.5" x2="14.5" y2="14.5"/><line x1="14.5" y1="9.5" x2="9.5" y2="14.5"/></svg>'
                    elif "주의" in grade:
                        chip_bg, chip_border = "#87CEFA", "#6495ED"
                        icon_bg, icon_color = "rgba(255,255,255,0.55)", "#0C447C"
                        text_color, sub_color = "#0B2A4A", "#2B4F72"
                        chip_title, chip_sub = "주의", "의심 요소 발견"
                        chip_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
                    else:
                        chip_bg, chip_border = "#E0FFFF", "#00BFFF"
                        icon_bg, icon_color = "rgba(255,255,255,0.6)", "#00688B"
                        text_color, sub_color = "#08313F", "#2B6478"
                        chip_title, chip_sub = "안전", "사기 패턴 없음"
                        chip_icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7.5-3.5 7.5-9.5V6l-7.5-3-7.5 3v5.5C4.5 17.5 12 21 12 21z"/><path d="M9 12l2 2 4-4"/></svg>'

                    st.markdown(f"""
                        <div style="background-color:{chip_bg}; border:1.5px solid {chip_border}; border-radius:16px; padding:16px 20px; display:flex; align-items:center; gap:14px; margin-bottom:16px;">
                            <div style="width:40px; height:40px; border-radius:12px; background-color:{icon_bg}; color:{icon_color}; display:flex; align-items:center; justify-content:center; flex-shrink:0;">{chip_icon}</div>
                            <div>
                                <p style="margin:0; font-size:17px; font-weight:800; color:{text_color};">{chip_title}</p>
                                <p style="margin:2px 0 0 0; font-size:13px; font-weight:600; color:{sub_color};">{chip_sub}</p>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                        <div class="toss-card">
                            <p style="font-size:14px; font-weight:700; color:var(--c-text-secondary); margin-bottom:4px;">알림 요약</p>
                            <p style="font-size:16px; font-weight:600; color:var(--c-text); margin-bottom:16px; line-height:1.6;">{summary}</p>
                            <p style="font-size:14px; font-weight:700; color:var(--c-text-secondary); margin-bottom:4px;">왜 사기로 판단했나요?</p>
                            <p style="font-size:15px; color:var(--c-text-secondary); line-height:1.6; margin-bottom:16px;">{reasons}</p>
                            <div style="height:1px; background-color:var(--c-bg); margin:16px 0;"></div>
                            <p style="font-size:14px; font-weight:700; color:var(--c-primary); margin-bottom:4px;">지금 하셔야 할 행동</p>
                            <p style="font-size:15px; font-weight:600; color:var(--c-primary); line-height:1.7;">{action}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if generate_card and "안심" not in grade:
                        copy_text = (
                            "[금융 사기 위험 발생 알림]\n"
                            "부모님 보안망에서 감지된 실시간 금융 조작 경고장\n\n"
                            f"감지 정황\n{_to_plain(summary_raw)}\n\n"
                            f"대응 수칙\n{_to_plain(action_raw)}\n\n"
                            "해당 화면을 즉시 캡처하여 자녀 및 가까운 지인에게 카카오톡으로 전송하세요."
                        )
                        copy_js = json.dumps(copy_text)

                        st.markdown(f"""
                            <div style="background-color:#191970; padding:28px; border-radius:22px; margin-top:20px; position:relative;">
                                <button onclick="navigator.clipboard.writeText({copy_js}); this.querySelector('span').innerText='복사됨';"
                                    style="position:absolute; top:18px; right:18px; background-color:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.28); color:#FFFFFF; border-radius:9px; padding:7px 12px; font-size:12.5px; font-weight:600; display:flex; align-items:center; gap:5px; cursor:pointer;">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                    <span>복사</span>
                                </button>
                                <div style="text-align:center; padding-right:64px;">
                                    <span style="display:inline-block; background-color:#E53E3E; color:#FFFFFF !important; padding:4px 10px; border-radius:6px; font-size:11px; font-weight:700;">가족 안심 경고 서신</span>
                                </div>
                                <div style="text-align:center; margin:14px 0 4px 0; display:flex; align-items:center; justify-content:center; gap:8px;">
                                    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                                    <span style="color:#FFFFFF !important; font-size:19px; font-weight:800;">금융 사기 위험 발생 알림</span>
                                </div>
                                <p style="text-align:center; color:#A9B4D6; font-size:13px; margin-bottom:20px;">부모님 보안망에서 감지된 실시간 금융 조작 경고장</p>
                                <div style="border-top:1px solid rgba(255,255,255,0.16); border-bottom:1px solid rgba(255,255,255,0.16); padding:18px 0; margin-bottom:14px; text-align:left;">
                                    <p style="font-size:13px; font-weight:700; color:#8FA3E8; margin-bottom:6px; letter-spacing:0.2px;">감지 정황</p>
                                    <p style="font-size:15px; font-weight:500; color:#F5F7FC; line-height:1.6; margin-bottom:16px;">{summary}</p>
                                    <p style="font-size:13px; font-weight:700; color:#8FA3E8; margin-bottom:6px; letter-spacing:0.2px;">대응 수칙</p>
                                    <p style="font-size:15px; font-weight:500; color:#F5F7FC; line-height:1.7; margin-bottom:0;">{action}</p>
                                </div>
                                <p style="font-size:12px; color:#8B95A1; margin-bottom:0; text-align:center;">해당 화면을 즉시 캡처하거나 위 복사 버튼을 눌러 자녀 및 가까운 지인에게 전송하세요.</p>
                            </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ 보안망 파싱 분석 도중 기술적 결함이 발생했습니다: {e}")

# ----------------- TAB 2: 최신 사기 Top 3 -----------------
with tab2:
    st.write("")
    st.markdown("<h4 style='font-size: 18px; font-weight: 700; margin-bottom: 16px;'>교활하게 진화한 다빈도 은퇴층 표적 범죄</h4>", unsafe_allow_html=True)

    st.markdown("""
        <div class="toss-card">
            <span class="badge badge-red">2025년 최다 유형 (51%)</span>
            <h5 style="margin:0 0 6px 0; font-size:17px; font-weight:700;">검찰·경찰·금융감독원 등 기관 사칭</h5>
            <p style="margin:0; font-size:14px; color:var(--c-text-secondary); line-height:1.6;">2016년 대비 발생 건수가 약 4배 늘며 전체 보이스피싱의 절반 이상을 차지하는 최다 유형이 됐습니다. 실제 기관 번호로 표시되도록 발신번호를 조작해 신뢰를 얻은 뒤 '안전 계좌' 이체를 요구합니다.</p>
        </div>
        <div class="toss-card">
            <span class="badge badge-sky">중장년층 집중 표적</span>
            <h5 style="margin:0 0 6px 0; font-size:17px; font-weight:700;">가족 사칭 (엄마 폰 고장났어 카톡 문자)</h5>
            <p style="margin:0; font-size:14px; color:var(--c-text-secondary); line-height:1.6;">보이스피싱 피해자 중 50대 이상 비중이 2023년 32%에서 2025년 53%까지 늘었습니다. 자녀의 실명과 말투를 흉내내어 급박한 수리비 대납이나 인증서 대리 발급을 유도합니다.</p>
        </div>
        <div class="toss-card">
            <span class="badge badge-sky">생활 침투형</span>
            <h5 style="margin:0 0 6px 0; font-size:17px; font-weight:700;">부고 알림장 및 주소 변경 확인 메시지</h5>
            <p style="margin:0; font-size:14px; color:var(--c-text-secondary); line-height:1.6;">모르는 번호로 전달된 경조사 안내 링크를 터치하는 순간, 부모님의 스마트폰에 저장된 모든 사진, 개인 정보, 공인인증서가 즉각 탈취됩니다.</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("📈 가장 빈번한 '기관 사칭' 수법 실시간 상세 대처법 열람하기", use_container_width=True):
        show_detail_guide("01 검찰·금융감독원 사칭 협박", fraud_db["01 검찰·금융감독원 사칭 협박"])

    st.caption("출처: 경찰청 국가수사본부 발표 자료, 공공데이터포털(data.go.kr) 「경찰청_보이스피싱 현황」 (2025년 기준)")

# ----------------- TAB 3: 유형별 대응법 -----------------
with tab3:
    st.write("")
    st.markdown("<h4 style='font-size: 18px; font-weight: 700; margin-bottom: 4px;'>알고 싶은 금융 사기 유형을 선택해 주세요</h4>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 14px; color: var(--c-text-secondary); margin-bottom: 20px;'>목록을 누르시면 실제 범죄 예시와 완벽한 방어 수칙 팝업창이 열립니다.</p>", unsafe_allow_html=True)

    for title, content_block in fraud_db.items():
        if st.button(f"➔ {title}", key=f"btn_{title}", use_container_width=True):
            show_detail_guide(title, content_block)

# ----------------- TAB 4: 긴급 신고 -----------------
with tab4:
    st.write("")
    st.markdown("<div class='toss-card' style='background-color:var(--c-danger-tint); border:1px solid #FFA39E;'><h4 style='color:var(--c-danger); margin:0; font-weight:800;'>🚨 혹시 이미 돈을 송금하셨거나 링크를 누르셨나요?</h4><p style='margin:8px 0 0 0; color:#5C0011; font-weight:600; font-size:14px;'>피싱 범죄는 초기 10분의 대처가 자산을 지키는 유일한 골든타임입니다.</p></div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("<p style='font-size:15px; font-weight:700; color:var(--c-text); margin-bottom:10px;'>[Step 1] 즉시 전화 신고로 지급 정지 신청</p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13px; color:var(--c-text-secondary); margin-bottom:10px;'>버튼을 누르시면 통화 시 당황하지 않고 즉시 사용할 수 있는 정부 표준 신고 대본이 열립니다.</p>", unsafe_allow_html=True)

    col_em1, col_em2, col_em3 = st.columns(3)

    if col_em1.button("📞 경찰청 사건 접수 (112)", key="call_112", use_container_width=True):
        show_emergency_script(
            "경찰청 긴급 범죄신고 센터", "112",
            "“방금 보이스피싱(또는 스미싱 문자) 사기단에게 속아 자금을 송금했습니다.\n"
            "사기단이 자금을 출금하거나 다른 계좌로 빼돌리지 못하도록, 제가 송금한 금융회사 계좌에 대해 긴급 지급정지 조치를 요청합니다.”"
        )

    if col_em2.button("📞 금융감독원 피해 접수 (1332)", key="call_1332", use_container_width=True):
        show_emergency_script(
            "금융감독원 보이스피싱 피해조사국", "1332",
            "“문자 사기로 계좌 정보와 신분증 사진이 노출되었습니다.\n"
            "추가적인 예금 인출이나 카드 부정 발급 등 2차 금융 피해가 발생하지 않도록 제 명의의 전 금융권 계좌에 대한 긴급 거래 제한 및 조회를 신청합니다.”"
        )

    if col_em3.button("📞 KISA 스미싱 신고 (118)", key="call_118", use_container_width=True):
        show_emergency_script(
            "한국인터넷진흥원(KISA) 인터넷침해대응센터", "118",
            "“스미싱 문자를 받고 링크를 눌러 악성 앱이 설치된 것 같습니다.\n"
            "스미싱 문자 내용과 발신번호를 신고하고, 스마트폰 내 악성 앱 확인 및 조치 방법을 안내받고 싶습니다.”"
        )

    st.write("")
    st.markdown("<p style='font-size:15px; font-weight:700; color:var(--c-text); margin-bottom:10px;'>[Step 2] 인터넷 웹사이트 원스톱 명의 보호망</p>", unsafe_allow_html=True)
    st.link_button("내 모든 계좌 돈 출금 한 번에 막기 (어카운트인포)", "https://www.accountinfo.or.kr", use_container_width=True)
    st.link_button("내 명의로 몰래 스마트폰 개통 차단하기 (M-Safer)", "https://www.msafer.or.kr", use_container_width=True)

    st.write("")
    st.markdown('<p class="field-label">아래 문장을 눌러 전체 복사한 후, 가족 카카오톡방에 전송해 상황을 전파하세요</p>', unsafe_allow_html=True)
    report_template = (
        "[긴급 보호 요청]\n"
        "부모님 스마트폰 보안망에서 치명적인 금융사기(피싱) 의심 신호가 감지되었습니다.\n"
        "자금 이체 및 추가 대화를 차단하고 있으니 본 메시지를 확인하는 즉시 부모님께 직접 음성 통화를 걸어 안전을 확인해 주세요."
    )
    st.text_area("가족 공유용 안내 문구", value=report_template, height=120, label_visibility="collapsed")
