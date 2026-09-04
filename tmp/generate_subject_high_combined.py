from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parent / "참고자료" / "공통자료"
SOURCE_DIR = ROOT.parent / "참고자료" / "사용한 원고" / "전국수업.com 추가 원고"
CENTER_INFO = COMMON / "센터정보 정리.csv"
REPRESENTATIVE_CSV = COMMON / "대표 이미지 url.csv"
LEVEL = os.environ.get("SUBJECT_LEVEL", "high").strip().lower()
CONFIGS = {
    "high": {
        "zip": "고등 영수학원.zip",
        "category": "고등영수학원",
        "display": "고등 영수학원",
        "level": "고등",
        "grade_prefix": "고",
        "audience": "고등학생",
        "eyebrow": "High School English & Math",
        "card_small": "고등학생 · 영어와 수학",
        "card_description": "371개 동네별 학습 진단·내신·오답 관리 안내",
        "school_field": "타깃학교(고)",
        "kind": "combined",
    },
    "middle": {
        "zip": "중등 영수학원.zip",
        "category": "중등영수학원",
        "display": "중등 영수학원",
        "level": "중등",
        "grade_prefix": "중",
        "audience": "중학생",
        "eyebrow": "Middle School English & Math",
        "card_small": "중학생 · 영어와 수학",
        "card_description": "371개 동네별 학교 내신·과제·오답 관리 안내",
        "school_field": "타깃학교(중)",
        "kind": "combined",
    },
    "elementary": {
        "zip": "초등 영수학원.zip",
        "category": "초등영수학원",
        "display": "초등 영수학원",
        "level": "초등",
        "grade_prefix": "초",
        "audience": "초등학생",
        "eyebrow": "Elementary English & Math",
        "card_small": "초등학생 · 영어와 수학",
        "card_description": "371개 동네별 기초 개념·학습 습관·오답 관리 안내",
        "school_field": "타깃학교(초)",
        "kind": "combined",
    },
    "math": {
        "zip": "수학학원.zip",
        "category": "수학학원",
        "display": "수학학원",
        "level": "수학",
        "subject": "수학",
        "grade_prefix": "",
        "audience": "초·중·고 학생",
        "eyebrow": "Math Learning Guide",
        "card_small": "초·중·고 · 수학",
        "card_description": "371개 동네별 개념·풀이·오답·복습 기준 안내",
        "school_field": "",
        "kind": "subject",
    },
    "english": {
        "zip": "영어학원.zip",
        "category": "영어학원",
        "display": "영어학원",
        "level": "영어",
        "subject": "영어",
        "grade_prefix": "",
        "audience": "초·중·고 학생",
        "eyebrow": "English Learning Guide",
        "card_small": "초·중·고 · 영어",
        "card_description": "371개 동네별 어휘·구문·독해·복습 기준 안내",
        "school_field": "",
        "kind": "subject",
    },
    "high_student": {
        "zip": "고등학생학원.zip",
        "category": "고등학생학원",
        "display": "고등학생학원",
        "level": "고등",
        "grade_prefix": "고",
        "audience": "고등학생",
        "eyebrow": "High School Learning Guide",
        "card_small": "고등학생 · 학년별 학습관리",
        "card_description": "371개 동네별 내신·모의 학습·시간관리 안내",
        "school_field": "타깃학교(고)",
        "kind": "student",
    },
    "middle_student": {
        "zip": "중학생학원.zip",
        "category": "중학생학원",
        "display": "중학생학원",
        "level": "중등",
        "grade_prefix": "중",
        "audience": "중학생",
        "eyebrow": "Middle School Learning Guide",
        "card_small": "중학생 · 내신과 학습습관",
        "card_description": "371개 동네별 학교 진도·과제·오답 관리 안내",
        "school_field": "타깃학교(중)",
        "kind": "student",
    },
    "elementary_student": {
        "zip": "초등학생학원.zip",
        "category": "초등학생학원",
        "display": "초등학생학원",
        "level": "초등",
        "grade_prefix": "초",
        "audience": "초등학생",
        "eyebrow": "Elementary Learning Guide",
        "card_small": "초등학생 · 기초와 공부습관",
        "card_description": "371개 동네별 기초 과목과 학습루틴 안내",
        "school_field": "타깃학교(초)",
        "kind": "student",
    },
}
if LEVEL not in CONFIGS:
    raise ValueError(f"Unsupported SUBJECT_LEVEL: {LEVEL}")
CONFIG = CONFIGS[LEVEL]
ZIP_PATH = SOURCE_DIR / CONFIG["zip"]
CATEGORY = CONFIG["category"]
CATEGORY_DISPLAY = CONFIG["display"]
LEVEL_LABEL = CONFIG["level"]
SUBJECT_LABEL = CONFIG.get("subject", "")
SCHOOL_LEVEL_LABEL = "학교" if CONFIG["kind"] == "subject" else {"고등": "고등학교", "중등": "중학교", "초등": "초등학교"}[LEVEL_LABEL]
GRADE_PREFIX = CONFIG["grade_prefix"]
AUDIENCE_LABEL = CONFIG["audience"]
EYEBROW_LABEL = CONFIG["eyebrow"]
TARGET = ROOT / "과목별학원" / CATEGORY
DOMAIN = "https://xn--3e0bz50bxucwzc.com"
SITE_NAME = "와와센터 학습코칭"
PUBLIC_SITE_NAME = "전국수업.com"
PHONE = "010-6839-8283"
PHONE_LINK = "01068398283"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"
SMS_URL = "https://blogsms.net/01068398283"
DATE_PUBLISHED = date.today().isoformat()
DATE_MODIFIED = date.today().isoformat()


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value or "").strip()


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


SCHOOL_NAME_RE = re.compile(
    r"(?<![가-힣A-Za-z0-9])"
    r"([가-힣A-Za-z0-9]{1,24}(?:초등학교|중학교|고등학교|초|중|고))"
    r"(?=$|[\s,.;:!?()\[\]·/]|은|는|이|가|을|를|과|와|도|만|의|처럼|에서|에는|으로|로|부터|까지|입니다|이고|이며)"
)
GENERIC_SCHOOL_RE = re.compile(
    r"(?:지역\s*내|관내|인근|주변).*(?:모든|전체)?.*학교.*가능|"
    r"(?:모든|전체)\s*(?:초등학교|중학교|고등학교)\s*가능"
)
UNVERIFIED_OPERATION_RE = re.compile(
    r"(?:입시\s*(?:컨설팅|전문)\s*학원|집중\s*관리\s*수업|코칭\s*수업|"
    r"입시(?:관리|코칭)학원|쾌적한학원|"
    r"학원(?:고객관리시스템|고객관리|수강생관리|온라인등록|개별지도|방역관리|안전관리|"
    r"출입관리|수준별수업|상담직원|커리큘럼|집중반|알림톡|알림장|매니저|"
    r"브랜드|시간표|주차|시설|일대일|보충|출결|수업|위치|등원|환경|교재|"
    r"소식|진도|과제)|"
    r"방학\s*특강|학원\s*보강|학원\s*맞춤\s*수업|소수\s*정예(?:\s*수업)?|주말\s*수업|입시\s*상담|"
    r"(?:학원\s*)?(?:온라인|대면|화상|실시간)\s*수업|"
    r"학원\s*(?:원장|강사|직원|창업|자습실|스터디룸|상담실|강의실|휴게실|사물함|"
    r"교재실|자료실|셔틀|차량|특강|설명회|예약\s*관리|전자\s*계약|문자\s*발송|"
    r"미납\s*관리|출결\s*앱|데스크|데이터\s*관리|코디네이터|개인정보\s*관리|"
    r"결제\s*(?:관리|시스템)|수납\s*관리|문서\s*관리|관리\s*(?:앱|프로그램|솔루션)))"
)
SUBJECT_NAMES = ("국어", "영어", "수학", "과학", "사회")
SUBJECT_CLAIM_RE = re.compile(
    r"(?<![가-힣A-Za-z0-9])(" + "|".join(SUBJECT_NAMES) + r")"
    r"(?=(?:에서|에게|으로|로|보다|부터|까지|[은는이가을를과와도만의에]|[·,/()\s]|$))"
)
AUTHORING_SIGNAL_RE = re.compile(
    r"CSV|데이터|입력된(?:\s+범위)?|입력\s*범위|수업학교\s*칸|"
    r"과목\s*참고\s*(?:키워드|확인\s*항목)|참고어|세부\s*소재|"
    r"실제로\s*운영되는\s*항목"
)


def seeded_index(*values: str, modulo: int) -> int:
    digest = hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def split_school_names(value: str) -> list[str]:
    raw = clean_text(value)
    if not raw or GENERIC_SCHOOL_RE.search(raw):
        return []
    values: list[str] = []
    for chunk in re.split(r"[,，·./|;\n]+", value or ""):
        chunk = clean_text(chunk)
        if not chunk:
            continue
        matches = [clean_text(item) for item in SCHOOL_NAME_RE.findall(chunk)]
        if matches:
            values.extend(matches)
            continue
        tokens = [item for item in chunk.split() if SCHOOL_NAME_RE.fullmatch(item)]
        values.extend(tokens)
    return list(dict.fromkeys(values))


def safe_focus(center: dict, suffix: str) -> str:
    if CONFIG["kind"] == "subject":
        options = {
            "수학": [
                "개념 이해와 문제 적용의 연결", "풀이 과정과 계산 오류의 구분", "오답 원인과 재확인 순서",
                "학년별 수학 진도와 복습의 균형", "문장제 조건 해석과 식 세우기", "주간 수학 학습량과 점검 일정",
            ],
            "영어": [
                "어휘 인출과 누적 복습의 연결", "문장 구조 이해와 정확한 해석", "독해 근거와 오답 원인의 구분",
                "학년별 영어 진도와 복습의 균형", "문법 개념과 서술형 적용", "주간 영어 학습량과 점검 일정",
            ],
        }[SUBJECT_LABEL]
        return options[seeded_index(CATEGORY, center["slug"], suffix, modulo=len(options))]
    banks = {
        "고등": [
            "내신과 모의고사 학습의 시간 배분", "누적 단원과 현재 시험 범위의 연결", "과목별 오답 재현과 주간 계획",
            "학기 중·방학 중 목표 조정", "수행평가와 지필평가 준비 순서", "학년 단계에 맞춘 복습 일정",
        ],
        "중등": [
            "학교 진도와 시험 범위 연결", "수행평가·과제·오답 일정 관리", "중학교 내신과 복습 습관",
            "과목별 취약 원인과 주간 계획", "수업 후 재확인과 질문 기록", "학년별 학교 학습 적응",
        ],
        "초등": [
            "기초 개념과 공부 시작 습관", "학교 학습과 가정 복습의 연결", "읽기·연산·문장 이해 점검",
            "과제 시작과 마무리 습관", "기초 과목의 균형", "스스로 설명하는 학습 과정",
        ],
    }
    options = banks[LEVEL_LABEL]
    return options[seeded_index(CATEGORY, center["slug"], suffix, modulo=len(options))]


def extract_reference_term(body: str) -> str:
    patterns = [
        r"(?:^|[.!?]\s+)([^.!?\r\n]{1,50}?)\s+데이터의\s+과목\s+참고\s+키워드는",
        r"(?:^|[.!?]\s+)([^.!?\r\n]{1,50}?)\s+데이터의\s+과목\s+참고\s+확인\s+항목은",
        r"(?m)^([^\r\n.!?]{1,50}?)\s+데이터의\s+과목\s+참고\s+키워드는",
        r"(?m)^([^\r\n.!?]{1,50}?)\s+데이터의\s+과목\s+참고\s+확인\s+항목은",
    ]
    if LEVEL == "middle_student":
        patterns.extend([
            r"(?m)^##\s*.*?에서\s+([가-힣A-Za-z0-9· ]{1,24})(?:을|를)\s+볼\s+때\s+필요한\s+상담\s+기준\s*$",
            r"복습\s*간격,\s*([가-힣A-Za-z0-9· ]{1,24})\s+운영\s+방식이",
        ])
    patterns.extend([
        r"(?m)^##\s*.+?학원(?:과|와)\s*([가-힣A-Za-z0-9· ]{1,24})(?:을|를)\s*함께\s*비교할\s*때.*$",
        r"(?m)^##\s*.+?\s+학부모가\s+살펴볼\s+([가-힣A-Za-z0-9· ]{1,24})\s*$",
        r"(?m)^([가-힣A-Za-z0-9· ]{1,24})\s+항목\s+기준으로",
        r"(?m)^##\s*([가-힣A-Za-z0-9· ]{1,24})(?:과|와)\s*연결되는\s*수업\s*운영\s*기준\s*$",
        r"(?m)^##\s*([가-힣A-Za-z0-9· ]{1,24})(?:을|를)\s*찾는\s*학부모가\s+.+?\s+중학생학원에서\s+묻는\s+질문\s*$",
        r"(?m)^##\s*([가-힣A-Za-z0-9· ]{1,24})(?:과|와)\s*연결한\s*학습\s*루틴\s*$",
        r"(?m)^##\s*([가-힣A-Za-z0-9· ]{1,24})(?:을|를)\s*확인할\s*때\s*묻기\s*좋은\s*질문\s*$",
        r"([가-힣A-Za-z0-9· ]{1,24})까지\s*함께\s*살피면",
        r"([가-힣A-Za-z0-9· ]{1,24})\s*관련\s*학습\s*관리",
        r"([가-힣A-Za-z0-9· ]{1,24})\s*(?:키워드|확인\s*항목)가",
        r"([가-힣A-Za-z0-9· ]{1,24})(?:과|와)\s*관련된\s*요소",
        r"([가-힣A-Za-z0-9· ]{1,24})까지\s*함께\s*확인",
    ])
    for pattern in patterns:
        match = re.search(pattern, body or "")
        if match:
            term = clean_text(match.group(1)).strip(" ,·")
            if 1 < len(term) <= 24:
                return term
    return ""


def contains_authoring_signal(value: str, center: dict) -> bool:
    reference_term = center.get("reference_term", "")
    return bool(
        AUTHORING_SIGNAL_RE.search(value or "")
        or reference_term and reference_term in (value or "")
    )


def english_fact_bounded_sentence(center: dict, suffix: str, index: int) -> str:
    """Replace source-production commentary with useful English-learning copy."""
    locality = center["locality"]
    focus = safe_focus(center, f"{suffix}-natural-{index}")
    variants = [
        f"{locality} 영어 상담에서는 최근 단어 확인 기록과 지문 표시를 함께 보며 {with_josa(focus, '이', '가')} 필요한 지점을 구분합니다.",
        f"현재 교재에서 혼자 읽을 수 있는 범위와 설명이 필요한 문장을 나누고, {with_josa(focus, '을', '를')} 다음 점검 기준으로 정합니다.",
        "어휘·문장 구조·독해·쓰기 중 멈추는 단계를 확인한 뒤 한 주에 실행할 학습량을 조정합니다.",
        f"{locality} 학생의 영어 계획은 프로그램 이름보다 실제 답안, 해석 과정과 오답을 다시 설명할 수 있는지로 비교하는 편이 좋습니다.",
        f"{with_josa(focus, '을', '를')} 확인할 때에는 정답 수만 보지 않고 처음 막힌 문장과 수정 뒤의 설명을 함께 기록합니다.",
        "상담에서는 현재 가능한 과제와 도움이 필요한 과제를 나누고, 수업 뒤 다시 확인할 날짜와 방법을 구체적으로 묻습니다.",
        f"{locality} 영어 학습의 시작점은 최근 지문에서 단어·구문·내용 이해 중 시간이 오래 걸린 부분을 찾는 것입니다.",
        "학교 시험 범위와 개인 교재를 나란히 놓고, 새 진도와 누적 복습의 비중을 실제 공부 시간에 맞게 정합니다.",
        f"{with_josa(focus, '이', '가')} 필요한 학생이라면 짧은 문장부터 근거를 말하게 한 뒤 지문 단위로 적용 범위를 넓혀 갑니다.",
        "학부모는 성적 표현보다 이번 주에 바꿀 학습 행동, 확인 자료와 다음 상담 날짜가 남는지 살펴보는 편이 좋습니다.",
        "어휘는 기억 여부를, 문장 구조는 해석 근거를, 독해는 선택지 판단 이유를 각각 나누어 확인합니다.",
        f"{locality}에서 영어 수업을 비교할 때에는 학생이 배운 내용을 스스로 설명하고 같은 오류를 다시 고칠 수 있는지 확인합니다.",
    ]
    return variants[seeded_index(CATEGORY, center["slug"], suffix, str(index), modulo=len(variants))]


def english_fact_bounded_heading(center: dict, suffix: str) -> str:
    focus = safe_focus(center, f"{suffix}-heading")
    variants = [
        f"{center['locality']} 영어 학습에서 먼저 확인할 단계",
        "어휘·문장 구조·독해를 나누어 보는 기준",
        f"{with_josa(focus, '을', '를')} 주간 계획으로 연결하는 방법",
        "학교 일정과 영어 복습을 함께 맞추는 기준",
        "현재 교재와 영어 오답을 상담에 활용하는 방법",
        f"{center['locality']} 영어학원 상담에서 남길 확인 기록",
    ]
    return variants[seeded_index(CATEGORY, center["slug"], suffix, modulo=len(variants))]


def sanitize_subject_authoring(value: str, center: dict, suffix: str) -> str:
    if CONFIG["kind"] != "subject" or SUBJECT_LABEL != "영어":
        return value
    if suffix.startswith("heading-") and contains_authoring_signal(value, center):
        return english_fact_bounded_heading(center, suffix)
    output: list[str] = []
    replaced = 0
    for sentence in re.split(r"(?<=[.!?])\s+", clean_text(value)):
        if contains_authoring_signal(sentence, center):
            candidate = english_fact_bounded_sentence(center, suffix, replaced)
            replaced += 1
        else:
            candidate = sentence
        if candidate and candidate not in output:
            output.append(candidate)
    text = " ".join(output)
    text = text.replace("입력된 범위", "확인된 범위")
    text = text.replace("입력 범위", "확인된 범위")
    text = text.replace("원문 정보", "기재된 정보")
    text = text.replace("위치 확인용 원문", "위치 확인 정보")
    text = text.replace("원문이며", "기재된 정보이며")
    text = text.replace("제공된 값", "확인된 정보")
    text = text.replace("확인된 정보과", "확인된 정보와")
    text = text.replace("학습 학습", "학습")
    text = text.replace("페이지에서는", "상담에서는")
    text = text.replace("페이지에는", "상담 전에는")
    text = text.replace("페이지에서", "상담에서")
    return text


def with_josa(value: str, consonant_form: str, vowel_form: str) -> str:
    """Return value with the correct Korean particle based on its last Hangul syllable."""
    last_hangul = next((char for char in reversed(value) if "가" <= char <= "힣"), "")
    has_batchim = bool(last_hangul and (ord(last_hangul) - ord("가")) % 28)
    return value + (consonant_form if has_batchim else vowel_form)


def correct_term_josa(value: str, term: str) -> str:
    """Correct particles that remain after a verified phrase replaces a source keyword."""
    if not term:
        return value
    escaped = re.escape(term)
    last_hangul = next((char for char in reversed(term) if "가" <= char <= "힣"), "")
    has_batchim = bool(last_hangul and (ord(last_hangul) - ord("가")) % 28)
    copula = "이라는" if has_batchim else "라는"
    value = re.sub(rf"{escaped}(?:이라는|라는)", term + copula, value)
    for consonant_form, vowel_form in (("은", "는"), ("이", "가"), ("을", "를"), ("과", "와")):
        value = re.sub(
            rf"{escaped}(?:{consonant_form}|{vowel_form})",
            with_josa(term, consonant_form, vowel_form),
            value,
        )
    return value


def subject_scope(center: dict) -> str:
    subjects = center.get("subjects", [])
    if CONFIG["kind"] == "subject":
        return SUBJECT_LABEL
    return "·".join(subjects) if subjects else "과목별 학습"


def audience_for_center(center: dict) -> str:
    if CONFIG["kind"] != "subject" or SUBJECT_LABEL != "영어":
        return AUDIENCE_LABEL
    labels = [
        label
        for prefix, label in (("초", "초등학생"), ("중", "중학생"), ("고", "고등학생"))
        if any(grade.startswith(prefix) for grade in center.get("grades", []))
    ]
    return "·".join(labels) if labels else "학생"


def subject_learning_label(center: dict) -> str:
    scope = subject_scope(center)
    return scope if scope.endswith("학습") else f"{scope} 학습"


def subject_fact_sentence(center: dict) -> str:
    subjects = center.get("subjects", [])
    if not subjects:
        return "센터 자료에는 해당 학년의 수업 가능 과목이 기재되어 있지 않아 상담 시 개설 여부를 확인해야 합니다."
    scope = "·".join(subjects)
    return f"제공 자료에서 확인되는 {scope} 학습은 현재 교재, 과제, 오답 기록을 살핀 뒤 학생별 우선순위를 정해야 합니다."


def subjects_in_text(value: str) -> set[str]:
    """Return explicit school-subject claims without matching words such as 지역사회."""
    return set(SUBJECT_CLAIM_RE.findall(value or ""))


def align_subject_claims(value: str, center: dict) -> str:
    if CONFIG["kind"] != "student":
        return value
    confirmed = set(center.get("subjects", []))
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(value))
    output: list[str] = []
    for sentence in sentences:
        unverified = subjects_in_text(sentence) - confirmed
        if unverified:
            learning_label = subject_learning_label(center)
            if sentence.rstrip().endswith("?"):
                replacement = f"{center['locality']} {learning_label}에서 먼저 확인할 기준은 무엇인가요?"
            elif not re.search(r"[.!?]$", sentence) and len(sentence) <= 80:
                replacement = f"{learning_label}의 우선순위와 복습 기준"
            else:
                replacement = subject_fact_sentence(center)
            if replacement not in output:
                output.append(replacement)
            continue
        output.append(sentence)
    return " ".join(dict.fromkeys(item for item in output if item)).strip()


def polish_phrase(value: str, center: dict, suffix: str) -> str:
    text = clean_text(value)
    focus = safe_focus(center, suffix)
    locality = center["locality"]
    learning_scope = subject_learning_label(center)
    audience = audience_for_center(center)
    reference_term = center.get("reference_term", "")
    if reference_term:
        text = text.replace(reference_term, focus)
        compact_reference = reference_term.replace(" ", "")
        if compact_reference != reference_term:
            text = text.replace(compact_reference, focus)
    text = UNVERIFIED_OPERATION_RE.sub(focus, text)
    text = re.sub(
        rf"{re.escape(center['locality'])}\s+{re.escape(CATEGORY_DISPLAY)}\s+검색자의\s+궁금증은\s+대개\s+.*?로\s+모입니다\.",
        f"{center['locality']} {CATEGORY_DISPLAY} 상담에서는 현재 교재와 오답 기록, 학교 일정, 주간 학습 시간을 함께 확인하는 것이 좋습니다.",
        text,
        count=1,
    )
    text = re.sub(
        rf"{re.escape(locality)}\s+{re.escape(CATEGORY_DISPLAY)}\s+페이지는\s+.*?학부모님께\s+바로\s+답하기\s+위해\s+작성했습니다\.",
        f"{locality}에서 {with_josa(CATEGORY_DISPLAY, '을', '를')} 비교할 때는 현재 교재·과제·오답 기록과 학교 일정을 먼저 확인해야 합니다.",
        text,
    )
    text = re.sub(
        rf"제공\s*자료에\s*수업\s*학교명이\s*비어\s*있으므로\s*{re.escape(locality)}\s+{re.escape(CATEGORY_DISPLAY)}\s+페이지에서는\s*특정\s*학교명을\s*임의로\s*넣지\s*않습니다\.",
        f"제공 자료에 {locality} {SCHOOL_LEVEL_LABEL}명이 없어 특정 학교 진도를 단정하지 않습니다.",
        text,
    )
    text = re.sub(
        rf"{re.escape(locality)}\s+페이지에는\s+제공된\s+학교\s+목록이\s+없어",
        f"제공 자료에 {locality} 학교 목록이 없어",
        text,
    )
    text = re.sub(
        rf"학교명이\s+제공되지\s+않은\s+{re.escape(locality)}\s+페이지에서는",
        f"제공 자료에 {locality} 학교명이 없으므로",
        text,
    )
    text = re.sub(
        rf"{re.escape(locality)}\s+{re.escape(CATEGORY_DISPLAY)}에\s+연결된\s+학교명\s+자료가\s+비어\s+있어\s+이\s+페이지에서는",
        f"제공된 {locality} 학교명 자료가 비어 있어",
        text,
    )
    text = text.replace("이 페이지의 기준 학생은", f"{locality} 상담에서 먼저 살펴볼 학생은")
    text = re.sub(
        rf"{re.escape(locality)}\s+상담에서\s+먼저\s+살펴볼\s+학생은\s+.*?특징을\s+함께\s+가진\s+유형입니다\.",
        (
            f"{locality} 상담에서는 최근 교재와 오답 기록을 통해 "
            f"{with_josa(focus, '이', '가')} 필요한 지점을 먼저 살펴봅니다. "
            f"{with_josa(audience, '은', '는')} 학교 일정과 실제 공부 시간을 맞춘 뒤 "
            "짧은 확인 질문으로 이해한 내용을 설명하고 다음 과제를 스스로 정할 수 있는지 점검해야 합니다."
        ),
        text,
    )
    text = text.replace("기준의 이 페이지는", "기준 상담에서는")
    text = text.replace("확인 방법을 정보성으로 정리합니다.", "확인 방법을 구체적으로 살펴봅니다.")
    text = text.replace("페이지에서 확인해야 할 내용은", "상담에서 확인해야 할 내용은")
    text = re.sub(
        rf"{re.escape(locality)}\s+{re.escape(CATEGORY_DISPLAY)}\s+본문은\s+제공\s+자료에\s+없는\s+학교를\s+예시로\s+들지\s+않고\s+시험\s+대비\s+방식\s+중심으로\s+구성합니다\.",
        f"제공 자료에 {locality} 학교명이 없을 때에는 학교를 임의로 추가하지 않고 현재 시험 범위와 대비 방식부터 확인합니다.",
        text,
    )
    text = re.sub(
        rf"{re.escape(locality)}\s*{re.escape(CATEGORY_DISPLAY)}은\s+.*?확인하기\s+위한\s+안내\s+페이지입니다\.",
        f"{locality} {with_josa(CATEGORY_DISPLAY, '을', '를')} 비교할 때는 아이의 {learning_scope} 시작점, 학교 숙제, 하교 후 학습 루틴을 함께 확인해야 합니다.",
        text,
    )
    text = text.replace(
        "학생에게 특히 점검할 항목이 많은 페이지입니다.",
        "학생이라면 현재 단원의 이해·적용·복습 흐름을 먼저 점검해야 합니다.",
    )
    text = text.replace("상담 사례를 바탕으로 재구성한 후기 형식으로 보면,", "상담 상황을 바탕으로 살펴보면,")
    text = text.replace("실제 상담 질문을 참고해 만든 후기형 문장으로 보면,", "상담 질문을 기준으로 살펴보면,")
    text = text.replace("후기 형식으로 보면,", "상담 상황을 기준으로 보면,")
    text = re.sub(
        r"또\s+다른\s+(.+?)\s+학부모의\s+후기\s+형식에서는\s+(.+?)(?:이라는|라는)\s+표현보다\s+수업\s+뒤\s+남는\s+피드백이\s+도움이\s+되었다는\s+점을\s+강조할\s+수\s+있습니다\.",
        r"\1 학부모는 상담에서 \2의 실제 확인 기준과 수업 뒤 남는 피드백을 함께 비교했습니다.",
        text,
    )
    text = text.replace("더 현실적이었다고 정리할 수 있습니다.", "더 현실적인 선택 기준이 됩니다.")
    text = re.sub(r"[가-힣A-Za-z0-9·\s]{1,24}\s*항목\s*기준으로", f"{focus} 기준으로", text)
    text = re.sub(r"[가-힣A-Za-z0-9·\s]{1,24}\s*관련\s*학습\s*관리", focus, text)
    text = text.replace("필요한 수능을 앞둔", "필요한")
    text = text.replace("모의 학습", "모의고사 학습")
    text = text.replace("고등 학교", "고등학교")
    text = text.replace("중등 학교", "중학교")
    text = text.replace("초등 학교", "초등학교")
    text = text.replace("후기 예시으로 보면", "상담 상황 예시로 보면")
    text = text.replace("후기 예시", "상담 상황 예시")
    text = text.replace("시기을", "시기를")
    text = text.replace("확인 항목가", "확인 항목이")
    text = text.replace("학생와", "학생과")
    text = text.replace("학생라는", "학생이라는")
    text = text.replace("학원라는", "학원이라는")
    text = text.replace("점검를", "점검을")
    text = text.replace("연결과 연결해 살피면", "연결을 함께 살피면")
    text = text.replace("연결과 연결해", "연결을 함께 살펴")
    text = text.replace("검색자에게도", "학부모에게도")
    text = text.replace("정보성 페이지로서도", "상담 정보로서도")
    text = text.replace("페이지용", "상담 전 확인용")
    text = re.sub(
        r"[^.?!]*페이지에서도\s*성적\s*상승이나\s*입시\s*결과를\s*보장하는\s*표현은\s*사용하지\s*않습니다\.",
        " 단기간 결과보다 실제 학습 기록과 재풀이 변화를 확인해야 합니다.",
        text,
    )
    text = re.sub(r"(?<![가-힣])JSON-LD(?![A-Za-z])", "구조화 정보", text)
    text = re.sub(r"(?<![가-힣])원고에서는", "안내에서는", text)
    text = re.sub(r"(?<![가-힣])원고에는", "안내에는", text)
    text = re.sub(r"(?<![가-힣])원고의", "안내의", text)
    text = re.sub(r"(?<![가-힣])원고를", "안내를", text)
    text = re.sub(r"(?<![가-힣])원고가", "안내가", text)
    text = re.sub(r"(?<![가-힣])원고는", "안내는", text)
    text = re.sub(r"(?<![가-힣])원고에서", "안내에서", text)
    text = re.sub(r"(?<![가-힣])원고에도", "안내에도", text)
    text = re.sub(r"(?<![가-힣])원고(?![가-힣])", "안내", text)
    text = text.replace("그래서 이 안내는", "상담에서는")
    text = text.replace("이 안내는", "상담에서는")
    text = re.sub(r"\S+\s*페이지가\s*지역명만\s*바뀐\s*안내가\s*되지\s*않으려면", "지역별 학습 조건을 구체적으로 비교하려면", text)
    text = text.replace("키워드", "확인 항목")
    text = text.replace("확인 항목가", "확인 항목이")
    text = text.replace("확인 항목 항목", "확인 항목")
    text = text.replace("학습 관리 관리", "학습 관리")
    compact_locality = center["locality"].replace(" ", "")
    text = text.replace(f"{compact_locality}{CATEGORY_DISPLAY}", f"{center['locality']} {CATEGORY_DISPLAY}")
    text = text.replace(f"{center['locality']}{CATEGORY_DISPLAY}", f"{center['locality']} {CATEGORY_DISPLAY}")
    text = text.replace(
        f"{center['locality']}에서 {center['locality']} {CATEGORY_DISPLAY}",
        f"{center['locality']}에서 {CATEGORY_DISPLAY}",
    )
    text = text.replace("제공된 수업학교 정보", "제공된 학교 정보")
    text = text.replace("수업학교 정보", "학교 정보")
    text = text.replace("과목별 학습 학습을", "과목별 학습을")
    text = text.replace("과목별 학습 학습의", "과목별 학습의")
    text = text.replace("과목별 학습 학습에서", "과목별 학습에서")
    text = text.replace("기초 기초 개념", "기초 개념")
    text = text.replace("기초와 기초 과목의 균형", "기초를 포함한 과목별 균형")
    text = re.sub(
        r"(?P<need>[^,.!?]{6,80}?)(?P<particle>이|가)\s+필요한\s+"
        r"(?P<student>[^,.!?]{2,60}?학생)의\s+경우\s+"
        r"(?P=need)(?:이|가)\s+자리\s+잡으면",
        r"\g<need>\g<particle> 필요한 \g<student>은 이 기준을 주간 계획에 반영하면",
        text,
    )
    text = re.sub(
        r"(?P<need>[^,.!?]{6,80}?)(?P<particle>이|가)\s+필요한\s+"
        r"(?P<student>[^,.!?]{2,60}?학생)에게는\s+선행\s+속도보다\s+"
        r"(?P=need)(?:을|를)\s+수업\s+안에서\s+확인하는\s+구조가\s+더\s+중요합니다\.",
        r"\g<need>\g<particle> 필요한 \g<student>이라면, 선행 속도보다 이 실행 기준이 수업 안에서 지켜지는지를 확인해야 합니다.",
        text,
    )
    text = text.replace("연결과 연결한", "연결을 바탕으로 한")
    for audience in ("고등학생", "중학생", "초등학생"):
        text = text.replace(f"{audience} 학생", audience)
    for term in (
        focus, "순서", "관리", "복기", "절차", "체크", "연결", "조정", "배분",
        "우선순위", "피로도", "문제", "계획", "습관", "기록", "적응", "균형",
        "과정", "점검", "반복", "표현", "요약", "리딩", "맞는지", "있는지",
        "이어지는지", "경우",
    ):
        text = correct_term_josa(text, term)
    text = text.replace("과목별 학습 학습을", "과목별 학습을")
    text = text.replace("과목별 학습 학습의", "과목별 학습의")
    text = text.replace("과목별 학습 학습에서", "과목별 학습에서")
    text = text.replace("연결과 연결한", "연결을 바탕으로 한")
    text = text.replace("연결과 연결되는", "연결을 바탕으로 보는")
    text = text.replace("연결과 연결해 살피면", "연결을 함께 살피면")
    text = text.replace("연결과 연결해", "연결을 함께 살펴")
    text = text.replace("학교 학학교 학습", "학교 학습")
    text = text.replace("기초 기초 개념", "기초 개념")
    text = re.sub(r"([.!?])(?=[가-힣])", r"\1 ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def verified_school_sentence(center: dict, suffix: str) -> str:
    schools = center["schools"]
    if schools:
        joined = "·".join(schools)
        variants = [
            f"제공된 {SCHOOL_LEVEL_LABEL} 참고 정보에는 {with_josa(joined, '이', '가')} 기재되어 있으며, 실제 계획은 현재 시험 범위와 교재를 확인한 뒤 정합니다.",
            f"{center['locality']} 센터 자료의 {SCHOOL_LEVEL_LABEL} 참고 목록은 {joined}이며, 학교명만으로 수업 방식이나 수준을 단정하지 않습니다.",
            f"학교 학습 연결에는 제공 자료에 적힌 {with_josa(joined, '을', '를')} 참고하되, 최근 과제와 평가 범위를 상담에서 다시 확인합니다.",
            f"{with_josa(joined, '은', '는')} 제공된 {SCHOOL_LEVEL_LABEL} 참고 정보이며, 학생별 진도와 오답 기록을 함께 보아야 실제 우선순위를 정할 수 있습니다.",
        ]
    else:
        variants = [
            f"제공 자료에 {SCHOOL_LEVEL_LABEL}명이 별도로 기재되어 있지 않아 학교를 임의로 추가하지 않았으며, 상담에서 현재 학교와 학습 범위를 확인합니다.",
            f"{center['locality']} 센터 자료에는 {SCHOOL_LEVEL_LABEL} 참고 목록이 없어, 현재 교재와 학교 과제를 직접 확인해 계획에 반영합니다.",
        ]
    return variants[seeded_index(CATEGORY, center["slug"], suffix, modulo=len(variants))]


def contains_school_name(value: str, school: str) -> bool:
    if not value or not school:
        return False
    pattern = re.compile(
        rf"(?<![가-힣A-Za-z0-9]){re.escape(school)}"
        rf"(?=$|[\s,.;:!?()\[\]·/]|은|는|이|가|을|를|과|와|도|만|의|처럼|에서|에는|으로|로|부터|까지|입니다|이고|이며)"
    )
    return bool(pattern.search(value))


def school_names_in(value: str, center: dict) -> list[str]:
    return [school for school in center.get("all_schools", []) if contains_school_name(value, school)]


def sanitize_school_sentences(value: str, center: dict, suffix: str) -> str:
    text = clean_text(value)
    if not school_names_in(text, center):
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    output: list[str] = []
    replaced = False
    for index, sentence in enumerate(sentences):
        if school_names_in(sentence, center):
            candidate = verified_school_sentence(center, f"{suffix}-{index}")
            if candidate not in output:
                output.append(candidate)
            replaced = True
        else:
            output.append(sentence)
    if not replaced:
        return text
    return " ".join(dict.fromkeys(part for part in output if part)).strip()


def allowed_grade_tokens(center: dict) -> list[str]:
    if CONFIG["kind"] == "subject":
        return [grade.replace(" ", "") for grade in center["grades"]]
    return [grade.replace(" ", "") for grade in center["grades"] if grade.startswith(GRADE_PREFIX)]


def sanitize_grade_claims(value: str, center: dict, suffix: str) -> str:
    text = value
    allowed = allowed_grade_tokens(center)
    generic = audience_for_center(center)
    if CONFIG["kind"] == "subject":
        replacement = "·".join(allowed) if allowed else generic
        grade_pattern = re.compile(r"(?:초|중|고)\s*[1-6]")
        normalized_sentences: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", clean_text(text)):
            listed = {token.replace(" ", "") for token in grade_pattern.findall(sentence)}
            if len(listed) >= 2 and listed - set(allowed):
                normalized_sentences.append(
                    f"{replacement} 범위의 {SUBJECT_LABEL} 학습은 현재 교재와 오답 기록을 확인해 우선순위를 정해야 합니다."
                )
            else:
                normalized_sentences.append(sentence)
        text = " ".join(dict.fromkeys(normalized_sentences))
        index = 0
        def subject_repl(match: re.Match[str]) -> str:
            nonlocal index
            token = match.group(0).replace(" ", "")
            if token in allowed:
                return token
            if not allowed:
                return generic
            selected = allowed[seeded_index(CATEGORY, center["slug"], suffix, str(index), modulo=len(allowed))]
            index += 1
            return selected
        return grade_pattern.sub(subject_repl, text)
    full_patterns = {
        "고": r"고등\s*전\s*학년",
        "중": r"중등\s*전\s*학년|중학교\s*전\s*학년",
        "초": r"초등\s*전\s*학년|초등학교\s*전\s*학년",
    }
    replacement = "·".join(allowed) if allowed else generic
    if CONFIG["kind"] == "student":
        normalized_sentences: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", clean_text(text)):
            listed = {token.replace(" ", "") for token in re.findall(rf"{GRADE_PREFIX}\s*[1-6]", sentence)}
            if len(listed) >= 2 and listed - set(allowed):
                normalized_sentences.append(
                    f"{replacement} 학생은 현재 학교 일정과 {with_josa(safe_focus(center, suffix), '을', '를')} 함께 확인해 학습 우선순위를 정해야 합니다."
                )
            else:
                normalized_sentences.append(sentence)
        text = " ".join(dict.fromkeys(normalized_sentences))
    text = re.sub(full_patterns[GRADE_PREFIX], replacement, text)
    pattern = re.compile(rf"{GRADE_PREFIX}\s*[1-6]")
    index = 0
    def repl(match: re.Match[str]) -> str:
        nonlocal index
        token = match.group(0).replace(" ", "")
        if token in allowed:
            return token
        if not allowed:
            return generic
        selected = allowed[seeded_index(CATEGORY, center["slug"], suffix, str(index), modulo=len(allowed))]
        index += 1
        return selected
    return pattern.sub(repl, text)


def sanitize_fragment(value: str, center: dict, suffix: str, *, school: bool = True) -> str:
    text = sanitize_grade_claims(value, center, suffix)
    if school:
        text = sanitize_school_sentences(text, center, suffix)
    text = align_subject_claims(text, center)
    source_region = center.get("source_region", "")
    if source_region and source_region != center.get("region"):
        text = re.sub(rf"(?<![가-힣]){re.escape(source_region)}(?=\s)", center["region"], text)
    text = sanitize_subject_authoring(text, center, suffix)
    return polish_phrase(text, center, suffix)


def meta_description(value: str, title: str) -> str:
    description = clean_text(value)
    if len(description) < 70:
        supplement = f" {title}의 학습 진단, 학교 학습 연결, 과제와 오답 관리 기준을 함께 안내합니다."
        description = (description + supplement).strip()
    if len(description) <= 150:
        return description
    sentences = re.split(r"(?<=[.!?。])\s+", description)
    selected: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*selected, sentence]).strip()
        if len(candidate) > 150:
            break
        selected.append(sentence)
    shortened = " ".join(selected).strip()
    if len(shortened) >= 70:
        return shortened
    shortened = description[:147].rsplit(" ", 1)[0].rstrip(" ,·")
    return shortened + "..."


def escape(value: str) -> str:
    return html.escape(value or "", quote=True)


def absolute_url(*parts: str) -> str:
    path = "/" + "/".join(part.strip("/") for part in parts if part) + "/"
    return DOMAIN + quote(path, safe="/")


def parse_sections(text: str) -> dict[str, str]:
    marker = re.compile(r"^\[([^\]]+)\]\s*$", re.MULTILINE)
    aliases = {
        "상담 상황 예시": "학부모후기",
        "구조화 데이터용 요약": "JSON-LD 요약",
    }
    matches = list(marker.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        name = aliases.get(match.group(1).strip(), match.group(1).strip())
        sections[name] = text[match.end():end].strip()
    return sections


def parse_body(body: str) -> tuple[str, list[tuple[str, list[str]]]]:
    heading = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading.finditer(body))
    intro = body[: matches[0].start()].strip() if matches else body.strip()
    result: list[tuple[str, list[str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        paragraphs = [
            re.sub(r"\s*\n\s*", " ", block.strip())
            for block in re.split(r"\n\s*\n", body[match.end():end].strip())
            if block.strip()
        ]
        result.append((match.group(1).strip(), paragraphs))
    return re.sub(r"\s*\n\s*", " ", intro), result


def parse_faq(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^Q(\d+)\.\s*(.+?)\s*\n(?:A(?:\1)?\.\s*)?(.+?)(?=\n\s*Q\d+\.|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [
        (question.strip(), re.sub(r"\s+", " ", answer).strip())
        for _, question, answer in pattern.findall(text)
    ]


def parse_review(text: str) -> tuple[str, list[str]]:
    raw = (text or "").strip()
    if not raw:
        return "", []
    normalized = re.sub(r"[ \t]+", " ", raw)
    numbered = re.findall(
        r"(?:후기|상담\s*상황)(?:\s*예시)?\s*\d+\.\s*(.*?)(?=(?:\n\s*)?(?:후기|상담\s*상황)(?:\s*예시)?\s*\d+\.|\Z)",
        normalized,
        re.DOTALL,
    )
    quoted = re.findall(r"[“\"](.+?)[”\"]", normalized, re.DOTALL)
    paragraphs = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    note_parts = [
        paragraph for paragraph in paragraphs
        if paragraph.startswith("※")
        or re.search(r"(?:학부모)?후기는\s*실제.*재구성한\s*예시", paragraph)
        or re.search(r"실제\s*(?:이용자|수강생).*아닙", paragraph)
        or re.search(r"특정\s*(?:성적|결과).*(?:뜻하지|아닙|보장하지)", paragraph)
    ]
    if numbered:
        reviews = numbered
    elif quoted:
        reviews = quoted
    elif paragraphs:
        reviews = [paragraph for paragraph in paragraphs if paragraph not in note_parts]
    else:
        reviews = []
    reviews = [review.strip().strip("“”\"'") for review in reviews if review.strip()]
    return " ".join(note_parts), reviews


def localized_faq(pairs: list[tuple[str, str]], title: str, locality: str) -> list[tuple[str, str]]:
    if not pairs or any(locality in question or title in question for question, _ in pairs):
        return pairs
    question, answer = pairs[0]
    return [(f"{locality} {CATEGORY_DISPLAY} 상담에서 {question}", answer), *pairs[1:]]


def build_meta(center: dict, title: str) -> str:
    focus = safe_focus(center, "meta")
    scope = subject_scope(center)
    audience = audience_for_center(center)
    variants = [
        f"{title} 선택 전 {audience}의 학교 진도, {scope} 상태, {focus}, 통학과 상담 기준을 확인하세요.",
        f"{title}에서 확인할 {LEVEL_LABEL} 학습 진단, 학교 일정, {focus}, 과제·오답 관리와 상담 질문을 정리했습니다.",
        f"{title} 안내입니다. {audience}의 {scope} 시작점과 {focus}, 학교 학습·복습·상담 기준을 확인하세요.",
        f"{title} 상담 전 살펴볼 학교 학습 흐름, {focus}, {scope} 오답과 주간 계획을 제공 센터 정보로 정리했습니다.",
        f"{title}을 찾는 학부모를 위해 {audience}의 학년 단계, {focus}, 과제와 오답 점검 기준을 안내합니다.",
        f"{title} 비교에 필요한 {SCHOOL_LEVEL_LABEL} 일정, {scope} 상태, {focus}, 상담 전 확인 항목을 정리했습니다.",
    ]
    start = seeded_index(CATEGORY, center["slug"], "meta", modulo=len(variants))
    ordered = variants[start:] + variants[:start]
    for candidate in ordered:
        candidate = clean_text(candidate)
        if 70 <= len(candidate) <= 100:
            return candidate
    candidate = ordered[0]
    if len(candidate) < 70:
        candidate += " 실제 수업 조건은 상담에서 다시 확인해야 합니다."
    if len(candidate) > 100:
        candidate = candidate[:97].rsplit(" ", 1)[0].rstrip(" ,·") + "..."
    return candidate


def build_summary(center: dict, title: str) -> str:
    focus = safe_focus(center, "summary")
    scope = subject_scope(center)
    address = center["address"] or "상담에서 확인할 센터 위치"
    audience = audience_for_center(center)
    school_clause = (
        f"제공된 {SCHOOL_LEVEL_LABEL} 참고 정보는 {'·'.join(center['schools'])}이며"
        if center["schools"] else
        f"제공 자료에 {SCHOOL_LEVEL_LABEL}명이 별도로 기재되어 있지 않아 학교를 임의로 추가하지 않았으며"
    )
    availability = (
        "" if center["grades"] else
        " 센터 자료에는 해당 학년의 수업 가능 정보가 없어 개설 여부를 상담에서 확인해야 합니다."
    )
    variants = [
        f"{title}은 {center['locality']}의 {with_josa(audience, '과', '와')} 학부모가 학교 일정, {scope} 상태, {with_josa(focus, '을', '를')} 확인하도록 돕는 정보입니다. 제공 센터 주소는 {address}이고, {school_clause} 실제 계획은 최근 교재와 오답 기록을 확인한 뒤 조정합니다.{availability}",
        f"{title}에서는 {center['locality']} {audience}의 학년 단계와 {with_josa(focus, '을', '를')} 먼저 살펴봅니다. 센터 위치는 {address}이며, {school_clause} 수업 시간·교습비·반 편성은 상담에서 다시 확인해야 합니다.{availability}",
        f"{center['locality']}에서 {with_josa(CATEGORY_DISPLAY, '을', '를')} 비교할 때에는 과목 수보다 학교 학습과 {with_josa(focus, '이', '가')} 한 주 계획으로 이어지는지 확인해야 합니다. 제공 주소는 {address}이고, {school_clause} 학생별 우선순위는 실제 학습 자료를 근거로 정합니다.{availability}",
        f"{title}은 {audience}의 {scope} 시작점, 학교 과제, 오답과 복습 기록을 함께 보는 지역 안내입니다. {with_josa(focus, '을', '를')} 상담 기준으로 삼고, {address}의 제공 센터 정보와 {SCHOOL_LEVEL_LABEL} 자료만 사용했습니다.{availability}",
    ]
    return variants[seeded_index(CATEGORY, center["slug"], "summary", modulo=len(variants))]


FAQ_QUESTION_BANKS = [
    [
        "{locality} {display}은 어떤 학습 상황부터 확인해야 하나요?",
        "{locality}에서 {display} 상담을 시작할 때 무엇을 먼저 보나요?",
        "{locality} {audience}에게 맞는 학원을 판단하는 첫 기준은 무엇인가요?",
        "{locality} {display} 선택 전에 학생 상태를 어떻게 정리하면 좋나요?",
        "{locality} 학부모가 첫 상담에서 준비할 학습 기록은 무엇인가요?",
        "{locality} {audience}의 현재 학습 단계는 어떤 자료로 확인하나요?",
        "{locality} {display}이 학생에게 맞는지 무엇으로 판단하나요?",
        "{locality}에서 학년 단계에 맞는 학습 계획은 어떻게 정하나요?",
    ],
    [
        "{locality} {display}에서 영어와 수학의 우선순위는 어떻게 나누나요?",
        "{locality} {audience}의 과목별 학습량은 같은 기준으로 정하나요?",
        "영어와 수학을 함께 관리할 때 {locality} 학생이 확인할 점은 무엇인가요?",
        "{locality}에서 두 과목 계획이 겹치면 무엇부터 조정해야 하나요?",
        "{locality} {display} 상담에서 과목별 약점은 어떻게 구분하나요?",
        "{locality} 학생의 영어·수학 복습 시간을 어떻게 배분하면 좋나요?",
        "{locality} {audience}에게 필요한 과목별 진단은 무엇이 다른가요?",
        "{locality}에서 과목 수보다 먼저 확인할 학습 기준은 무엇인가요?",
    ],
    [
        "{locality} {display} 상담에서 학교 자료는 어떻게 활용하나요?",
        "{locality} 학생의 학교 진도와 학원 계획은 어떻게 연결하나요?",
        "학교명보다 최근 시험 범위를 먼저 확인해야 하는 이유는 무엇인가요?",
        "{locality} {audience}의 수행평가와 과제 일정은 어떻게 반영하나요?",
        "{locality}에서 학교 교재와 오답을 상담에 가져가야 하나요?",
        "{locality} {display}의 학교 학습 연결 기준은 무엇인가요?",
        "학교별 계획을 세울 때 {locality} 학부모가 확인할 자료는 무엇인가요?",
        "{locality} 학생의 현재 교재는 주간 계획에 어떻게 반영되나요?",
    ],
    [
        "{locality} {display} 상담에서 과제와 오답 관리는 어떻게 확인하나요?",
        "{locality} 학생의 주간 계획이 실제로 실행되는지 무엇으로 보나요?",
        "결석이나 일정 변경이 생기면 {locality} 학습 계획을 어떻게 조정하나요?",
        "{locality} {audience}의 복습 기록은 어느 간격으로 확인하나요?",
        "{locality} {display}에서 학습 습관을 판단하는 기준은 무엇인가요?",
        "{locality} 학부모 피드백에는 어떤 학습 기록이 포함되어야 하나요?",
        "{locality} 학생이 같은 오답을 반복할 때 무엇을 바꿔야 하나요?",
        "{locality}에서 무리하지 않는 과제량은 어떻게 정하나요?",
    ],
    [
        "{locality} {display} 방문 전에 주소 외에 무엇을 확인해야 하나요?",
        "{locality}에서 상담 결과를 비교할 때 어떤 질문을 같게 준비해야 하나요?",
        "단기간 결과보다 {locality} 학생의 어떤 변화를 확인해야 하나요?",
        "{locality} {display} 상담 후 첫 달에는 무엇을 점검하면 좋나요?",
        "{locality} 학부모가 수업 시간과 교습비 외에 물을 내용은 무엇인가요?",
        "{locality} 학생의 통학과 복습 시간이 맞는지 어떻게 확인하나요?",
        "{locality} {display} 설명을 실제 운영 조건과 어떻게 대조하나요?",
        "{locality} 상담에서 바뀔 수 있는 정보는 무엇을 다시 확인해야 하나요?",
    ],
]


def diversified_question(center: dict, index: int, original: str) -> str:
    if CONFIG["kind"] == "subject":
        # The subject manuscripts already contain page-specific, semantically
        # matched questions. Preserve them instead of replacing them with the
        # legacy combined English-and-math question bank.
        if SUBJECT_LABEL == "영어" and contains_authoring_signal(original, center):
            templates = [
                "{locality} 영어 상담에서 어휘·문장 구조·독해 중 무엇을 먼저 확인하나요?",
                "{locality} 학생의 영어 오답은 어떤 순서로 다시 점검하나요?",
                "{locality} 영어학원을 비교할 때 현재 교재에서 무엇을 살펴봐야 하나요?",
                "{locality} 영어 학습의 주간 목표와 복습일은 어떻게 정하나요?",
                "{locality} 학생이 문장을 이해했는지 어떤 설명으로 확인하나요?",
                "{locality} 영어 상담 뒤 첫 점검 항목은 무엇으로 정하면 좋나요?",
            ]
            template = templates[seeded_index(CATEGORY, center["slug"], "authoring-faq", str(index), modulo=len(templates))]
            return template.format(locality=center["locality"])
        return clean_text(original).replace("학습 학습", "학습")
    if "학교" in original or school_names_in(original, center):
        bank_index = 2
    else:
        bank_index = min(index, len(FAQ_QUESTION_BANKS) - 1)
    bank = FAQ_QUESTION_BANKS[bank_index]
    template = bank[seeded_index(CATEGORY, center["slug"], "faq", str(index), modulo=len(bank))]
    rendered = template.format(locality=center["locality"], display=CATEGORY_DISPLAY, audience=AUDIENCE_LABEL)
    return align_subject_claims(rendered, center)


def sanitize_page(page: dict, center: dict) -> dict:
    sections = dict(page["sections"])
    center["reference_term"] = extract_reference_term(sections["본문"])
    title = f"{center['locality']} {CATEGORY_DISPLAY}"
    sections["페이지타이틀"] = title
    sections["메타설명"] = build_meta(center, title)

    intro, body_sections = parse_body(sections["본문"])
    intro = sanitize_fragment(intro, center, "intro")
    cleaned_sections: list[tuple[str, list[str]]] = []
    seen_headings: set[str] = set()
    alternate_headings = [
        f"{center['locality']} 학생의 현재 교재와 오답을 확인하는 기준",
        "학교 일정과 과목별 계획을 함께 조정하는 방법",
        f"{AUDIENCE_LABEL}의 주간 복습 계획을 구체화하는 질문",
        "상담에서 학습 시작점과 다음 목표를 나누는 기준",
    ]
    for section_index, (heading, paragraphs) in enumerate(body_sections):
        if school_names_in(heading, center):
            heading = [
                f"{center['locality']} 학교 자료와 현재 학습 범위를 연결하는 방법",
                "제공 학교 정보는 상담에서 어떻게 활용해야 하나",
                f"{SCHOOL_LEVEL_LABEL} 일정과 학생별 계획을 함께 보는 기준",
            ][seeded_index(CATEGORY, center["slug"], "school-heading", str(section_index), modulo=3)]
        else:
            heading = sanitize_fragment(heading, center, f"heading-{section_index}", school=False)
        if heading in seen_headings:
            for offset in range(len(alternate_headings)):
                candidate = alternate_headings[(section_index + offset) % len(alternate_headings)]
                if candidate not in seen_headings:
                    heading = candidate
                    break
        seen_headings.add(heading)
        cleaned = [
            sanitize_fragment(paragraph, center, f"body-{section_index}-{paragraph_index}")
            for paragraph_index, paragraph in enumerate(paragraphs)
        ]
        cleaned_sections.append((heading, list(dict.fromkeys(item for item in cleaned if item))))
    sections["본문"] = intro + "\n\n" + "\n\n".join(
        "## " + heading + "\n\n" + "\n\n".join(paragraphs)
        for heading, paragraphs in cleaned_sections
    )

    faq_items = parse_faq(sections["FAQ"])
    cleaned_faq: list[tuple[str, str]] = []
    for index, (question, answer) in enumerate(faq_items):
        question_has_school = "학교" in question or bool(school_names_in(question, center))
        question = diversified_question(center, index, question)
        answer = verified_school_sentence(center, f"faq-{index}") if question_has_school else sanitize_fragment(answer, center, f"faq-{index}")
        cleaned_faq.append((question, answer))
    sections["FAQ"] = "\n\n".join(
        f"Q{index}. {question}\nA{index}. {answer}"
        for index, (question, answer) in enumerate(cleaned_faq, 1)
    )

    _, reviews = parse_review(sections["학부모후기"])
    cleaned_reviews = [sanitize_fragment(review, center, f"case-{index}") for index, review in enumerate(reviews)]
    note = f"※ {center['locality']} 학부모가 상담에서 확인할 상황을 재구성한 예시이며, 실제 수강 후기나 특정 성적 결과가 아닙니다."
    sections["학부모후기"] = note + "\n\n" + "\n\n".join(
        f"상담 상황 {index}. {review}" for index, review in enumerate(cleaned_reviews or [f"{center['locality']} 학생의 현재 교재와 오답을 확인한 뒤 주간 계획을 조정하는 상황입니다."], 1)
    )
    sections["JSON-LD 요약"] = build_summary(center, title)
    prepared = {**page, "sections": sections}
    assert_safe_page(prepared, center)
    return prepared


def assert_safe_page(page: dict, center: dict) -> None:
    sections = page["sections"]
    title = sections["페이지타이틀"]
    if title != f"{center['locality']} {CATEGORY_DISPLAY}":
        raise ValueError(f"Unexpected normalized title: {title}")
    description = sections["메타설명"]
    if not 70 <= len(description) <= 100:
        raise ValueError(f"Meta length {len(description)} for {title}")
    # The strict operation/fact wording rules below were introduced for the
    # student-stage guides.  Keep the legacy English+math generator usable
    # without retroactively rejecting its already published manuscript style.
    if CONFIG["kind"] != "student":
        return
    visible = "\n".join(sections.values())
    reference_term = center.get("reference_term", "")
    if LEVEL == "middle_student" and reference_term and any(
        candidate and candidate in visible
        for candidate in (reference_term, reference_term.replace(" ", ""))
    ):
        raise ValueError(f"Reference term remains {reference_term!r} in {title}")
    unsafe = UNVERIFIED_OPERATION_RE.search(visible)
    if unsafe:
        raise ValueError(f"Unverified operation term {unsafe.group(0)!r} in {title}")
    for broken in (
        "후기 예시으로", "시기을", "페이지용", "원고에서는", "JSON-LD", "관련 학습 관리",
        "확인 항목 항목", "확인 항목가", "학생와", "학생라는", "필요한 수능을 앞둔",
        "정보성 페이지로서도", "지역별 원고", "페이지에서도 성적 상승",
        "학습 학습", "기초 기초", "연결과 연결", "학교 학학교", "확인을 확인",
        "습관를", "학원라는", "검색자의 궁금증은", "고등 학교", "중등 학교", "초등 학교",
        "모의 학습", "페이지에서는", "페이지에는", "이 페이지의", "본문은",
        "작성했습니다", "안내 페이지입니다", "많은 페이지입니다", "후기 형식",
        "후기형 문장", "강조할 수 있습니다", f"{AUDIENCE_LABEL} 학생",
        "특징을 함께 가진 유형", "학생에게는 선행 속도보다",
    ):
        if broken in visible:
            raise ValueError(f"Broken phrase {broken!r} in {title}")
    if re.search(r"(?<![가-힣])원고(?:는|에서|에도|에서는|에는|의|를|가)?(?![가-힣])", visible):
        raise ValueError(f"Authoring voice remains in {title}")
    if re.search(r"학생의\s+경우\s+[^.!?]{6,120}?(?:이|가)\s+자리\s+잡으면", visible):
        raise ValueError(f"Repeated student-condition phrase remains in {title}")
    if center.get("source_region") != center.get("region") and re.search(
        rf"(?<![가-힣]){re.escape(center['source_region'])}(?=\s)", visible
    ):
        raise ValueError(f"Non-standard region remains in {title}")
    unverified_subjects = subjects_in_text(visible) - set(center["subjects"])
    if unverified_subjects:
        raise ValueError(f"Unverified subject claims in {title}: {sorted(unverified_subjects)}")
    allowed_schools = set(center["schools"])
    found_schools = {school for school in center.get("all_schools", []) if contains_school_name(visible, school)}
    unexpected_schools = found_schools - allowed_schools
    if unexpected_schools:
        raise ValueError(f"Unexpected schools in {title}: {sorted(unexpected_schools)}")
    allowed_grades = set(allowed_grade_tokens(center))
    found_grades = {item.replace(" ", "") for item in re.findall(rf"{GRADE_PREFIX}\s*[1-6]", visible)}
    if found_grades - allowed_grades:
        raise ValueError(f"Unexpected grades in {title}: {sorted(found_grades-allowed_grades)}")


def read_zip_entries() -> list[dict]:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(ZIP_PATH)
    pages: list[dict] = []
    with ZipFile(ZIP_PATH) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".txt"):
                continue
            text = archive.read(info).decode("utf-8-sig")
            sections = parse_sections(text)
            required = {"페이지타이틀", "메타설명", "본문", "FAQ", "학부모후기", "JSON-LD 요약"}
            missing = required - sections.keys()
            if missing:
                raise ValueError(f"{info.filename}: missing sections {sorted(missing)}")
            title = clean_text(sections["페이지타이틀"])
            locality = re.sub(rf"\s*{re.escape(CATEGORY_DISPLAY)}\s*$", "", title).strip()
            if not locality or normalize(title) != normalize(f"{locality} {CATEGORY_DISPLAY}"):
                raise ValueError(f"Unexpected title: {title}")
            sections["페이지타이틀"] = f"{locality} {CATEGORY_DISPLAY}"
            pages.append({"filename": info.filename, "locality": locality, "sections": sections})
    if len(pages) != 371:
        raise ValueError(f"Expected 371 manuscripts, found {len(pages)}")
    return pages


def read_center_rows() -> list[dict[str, str]]:
    with CENTER_INFO.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [{key.strip(): (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]
    if len(rows) != 371:
        raise ValueError(f"Expected 371 center rows, found {len(rows)}")
    return rows


def field(row: dict[str, str], prefix: str) -> str:
    for key, value in row.items():
        if key.replace("\n", "").startswith(prefix.replace("\n", "")):
            return value.strip()
    return ""


def split_values(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，]", value or "") if part.strip()]


def make_slugs(rows: list[dict[str, str]]) -> dict[str, str]:
    localities = [row["근처 수업가능 동네"] for row in rows]
    neighborhood_count = Counter(value.split()[-1] for value in localities)
    result: dict[str, str] = {}
    for locality in localities:
        neighborhood = locality.split()[-1]
        slug = neighborhood if neighborhood_count[neighborhood] == 1 else normalize(locality)
        result[normalize(locality)] = slug
    return result


def representative_urls() -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    sources: list[str] = []
    if REPRESENTATIVE_CSV.exists():
        sources.append(REPRESENTATIVE_CSV.read_text(encoding="utf-8-sig", errors="ignore"))
    else:
        # The original representative URL sheet was later reorganized. Reuse the
        # already-published remote representative pool so the hidden/OG image
        # convention remains stable without inventing a new external asset source.
        for page_path in sorted((ROOT / "과목별학원").glob("*/*/index.html")):
            source = page_path.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', source, re.IGNORECASE)
            if match:
                sources.append(match.group(1))
    for source in sources:
        for url in re.findall(r"https://[^\"',<>\s]+\.(?:jpg|jpeg|png|webp|gif)", source, re.IGNORECASE):
            if url.startswith("http") and url not in seen:
                seen.add(url)
                values.append(url)
    if not values:
        raise ValueError("No representative image URLs found")
    return values


def choose_representative(urls: list[str], title: str) -> str:
    digest = hashlib.sha256(f"{CATEGORY}|{title}".encode("utf-8")).hexdigest()
    return urls[int(digest[:12], 16) % len(urls)]


def map_source(row: dict[str, str], slug: str) -> str:
    map_name = row.get("동 영어", "").strip()
    candidates = [f"{map_name}.jpg", f"{map_name}.webp", f"{map_name}.png"] if map_name else []
    parent = ROOT / "전국센터" / slug / "index.html"
    if parent.exists():
        match = re.search(r"assets/maps/([^\"']+)", parent.read_text(encoding="utf-8", errors="ignore"))
        if match:
            candidates.insert(0, match.group(1))
    for name in candidates:
        if (ROOT / "assets" / "maps" / name).exists():
            return name
    raise FileNotFoundError(f"Map not found for {row.get('근처 수업가능 동네')}: {candidates}")


def image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(path) as image:
            return image.size
    except Exception as exc:
        raise RuntimeError(f"이미지 크기를 확인할 수 없습니다: {path}") from exc


def official_region(row: dict[str, str]) -> str:
    source = row.get("지역", "")
    if source not in {"충청", "경상", "전라"}:
        return source
    address = row.get("센터 주소", "").strip()
    mappings = [
        ("충북", "충청북도"), ("충청북도", "충청북도"),
        ("충남", "충청남도"), ("충청남도", "충청남도"),
        ("경북", "경상북도"), ("경상북도", "경상북도"),
        ("경남", "경상남도"), ("경상남도", "경상남도"),
        ("전북", "전북특별자치도"), ("전라북도", "전북특별자치도"), ("전북특별자치도", "전북특별자치도"),
        ("전남", "전라남도"), ("전라남도", "전라남도"),
        ("대전", "대전"), ("세종", "세종"), ("대구", "대구"), ("부산", "부산"),
        ("울산", "울산"), ("광주", "광주"),
    ]
    for prefix, normalized in mappings:
        if address.startswith(prefix):
            return normalized
    raise ValueError(f"공식 시도명을 주소에서 확인할 수 없습니다: {row.get('근처 수업가능 동네')} / {address}")


def grade_intersection(row: dict[str, str]) -> list[str]:
    if CONFIG["kind"] == "subject":
        return split_values(field(row, f"가능학년({SUBJECT_LABEL})"))
    if CONFIG["kind"] == "student":
        values: list[str] = []
        for subject in ("국어", "영어", "수학", "과학", "사회"):
            values.extend(split_values(field(row, f"가능학년({subject})")))
        return list(dict.fromkeys(grade for grade in values if grade.startswith(GRADE_PREFIX)))
    english_grades = split_values(field(row, "가능학년(영어)"))
    math_grades = split_values(field(row, "가능학년(수학)"))
    math_set = set(math_grades)
    return [grade for grade in english_grades if grade in math_set and grade.startswith(GRADE_PREFIX)]


def available_subjects(row: dict[str, str]) -> list[str]:
    if CONFIG["kind"] == "subject":
        return [SUBJECT_LABEL] if split_values(field(row, f"가능학년({SUBJECT_LABEL})")) else []
    subjects: list[str] = []
    for subject in ("국어", "영어", "수학", "과학", "사회"):
        if any(grade.startswith(GRADE_PREFIX) for grade in split_values(field(row, f"가능학년({subject})"))):
            subjects.append(subject)
    return subjects


def paragraph_html(value: str) -> str:
    return f"<p>{escape(re.sub(r'\\s*\\n\\s*', ' ', value.strip()))}</p>"


def local_context_html(center: dict, title: str) -> str:
    seed = int(hashlib.sha256(f"{CATEGORY}|{center['slug']}|context".encode("utf-8")).hexdigest()[:8], 16)
    headings = [
        f"{center['locality']}에서 상담 전에 맞춰 볼 실제 조건",
        f"{center['locality']} 학습 계획을 세울 때 확인할 지역 기준",
        f"{title} 상담을 구체화하는 정보",
        f"{center['locality']} 학생에게 맞는 일정을 판단하는 방법",
        "센터 정보와 학교 자료를 함께 보는 이유",
        f"{center['locality']} 수업 선택을 서두르지 않는 기준",
    ]
    region_line = " ".join(value for value in (center["region"], center["district"], center["locality"]) if value)
    grade_line = "·".join(center["grades"])
    grade_label = (
        "센터 전체 수업 가능 학년" if CONFIG["kind"] == "student" else
        f"{SUBJECT_LABEL} 가능 학년" if CONFIG["kind"] == "subject" else
        "영어·수학 공통 가능 학년"
    )
    grade_fact = (
        f"{grade_label}은 {grade_line}입니다."
        if grade_line
        else f"{grade_label}은 자료에 기재되지 않아 상담에서 확인해야 합니다."
    )
    grade_plan = (
        f"{grade_line} 범위에서 {subject_scope(center)} 우선순위를 정하는 편이 좋습니다."
        if grade_line
        else f"수업 대상 학년은 상담에서 확인한 뒤 {subject_scope(center)} 우선순위를 정하는 편이 좋습니다."
    )
    school_line = "·".join(center["schools"])
    address = center["address"] or "상담 시 확인하는 센터 위치"
    scope = subject_scope(center)
    learning_scope = subject_learning_label(center)
    first_variants = [
        f"{region_line}에서 {with_josa(CATEGORY_DISPLAY, '을', '를')} 살필 때에는 과목명만 비교하기보다 실제 이동 경로와 가능한 수업 학년을 함께 확인해야 합니다. 제공된 센터 위치는 {address}입니다. {grade_fact}",
        f"{title} 상담은 학생의 현재 교재와 최근 오답을 확인한 뒤 현실적인 통원 일정까지 맞추는 과정입니다. {region_line}의 제공 센터 주소는 {address}입니다. {grade_fact}",
        f"{region_line}에서 수업을 이어 가려면 계획의 양보다 꾸준히 방문하고 복습할 수 있는지가 중요합니다. {with_josa(address, '을', '를')} 기준으로 이동 시간을 먼저 살핍니다. {grade_plan}",
        f"{title}을 알아보는 단계에서는 주소와 학년 정보를 먼저 맞춰야 상담 내용이 구체적이 됩니다. 제공 자료의 센터 위치는 {address}입니다. {grade_fact}",
        f"{region_line} 학생의 {learning_scope}을 관리하려면 학교 일정, 통원 시간, 복습 가능 시간을 한 흐름으로 봐야 합니다. 센터 위치는 {address}입니다. {grade_fact} 최근 학습 기록을 준비해 상담하는 방식이 적절합니다.",
        f"{title} 선택에서 먼저 확인할 것은 학생이 실제로 다닐 수 있는 위치와 수업 대상입니다. 제공된 센터 위치는 {address}입니다. {grade_fact} 최종 시간표는 상담에서 다시 맞춥니다.",
    ]
    second_variants = [
        f"{center['locality']} 학교 학습 연결을 확인할 때 참고할 제공 학교 목록은 {school_line}입니다. 학교명은 수업 가능 여부를 단정하는 기준이 아니라 상담 전에 시험 범위와 사용 교재를 준비하기 위한 참고 정보로 활용합니다.",
        f"{center['locality']} 제공 자료에는 {with_josa(school_line, '이', '가')} 학교 참고 목록으로 정리되어 있습니다. 해당 학교 학생이라면 최근 시험지나 주간 과제를 가져와 {learning_scope}에서 먼저 조정할 부분을 구체적으로 확인하는 것이 좋습니다.",
        f"{center['locality']} 학교별 진도와 평가 방식은 같지 않으므로 {school_line} 등 제공 학교 정보는 상담 준비의 출발점으로만 사용합니다. 실제 계획은 학생이 사용하는 교재, 시험 범위, 오답 기록을 확인한 뒤 결정합니다.",
        f"{center['locality']}의 제공 학교 참고 목록은 {school_line}입니다. 학교 이름을 반복해 홍보하기보다 현재 범위와 학생의 풀이 기록을 함께 확인해야 과목별 학습 순서를 현실적으로 정할 수 있습니다.",
        f"{with_josa(school_line, '은', '는')} {center['locality']} 센터 자료에 포함된 학교 참고 정보입니다. 같은 학교 학생이라도 취약 단원과 공부 시간이 다르므로 학교명만으로 수업 방식을 정하지 않고 개별 자료를 바탕으로 상담합니다.",
        f"{center['locality']} 학교 학습과의 연결은 제공 목록인 {with_josa(school_line, '을', '를')} 참고하되, 실제 수업 판단은 최근 시험 범위와 오답 유형을 중심으로 진행합니다. 제공되지 않은 학교나 생활권 정보는 임의로 추가하지 않았습니다.",
    ]
    registration = center["registration"] or "상담 시 확인하는 등록 정보"
    center_name = center["center"] or f"{center['locality']} 학습센터"
    third_variants = [
        f"상담에서 확인할 센터는 {center_name}이며 제공 등록 정보는 {registration}입니다. {center['locality']} 상담에서는 등록 정보와 교습비 링크가 실제 수업 횟수·교재·보강 조건과 어떻게 연결되는지도 함께 확인합니다.",
        f"{center_name}의 제공 자료에는 {with_josa(registration, '이', '가')} 표시되어 있습니다. {center['locality']} 학부모는 이 정보와 교습비 자료를 확인한 뒤 수업 시간뿐 아니라 과제 확인과 재학습 방식까지 질문하는 편이 좋습니다.",
        f"{center['locality']} 상담에서는 {center_name}, {with_josa(registration, '을', '를')} 센터 확인 자료로 사용합니다. 등록 여부만으로 수업 적합성을 단정하지 않고 학생 기록과 실제 상담 조건을 함께 비교해야 합니다.",
        f"제공된 센터명은 {center_name}, 등록 정보는 {registration}입니다. {center['locality']}에서 상담할 때에는 표시된 정보가 현재 시간표와 교습비 조건에도 동일하게 적용되는지 다시 확인합니다.",
        f"{center_name}에 대해 제공된 등록 자료는 {registration}입니다. {center['locality']} 학생의 {scope} 계획은 이 기본 정보에 더해 최근 시험지와 오답 기록을 확인한 뒤 구체화합니다.",
        f"{center['locality']} 수업 안내의 기준 센터는 {center_name}이며 자료에 기재된 등록 정보는 {registration}입니다. 상담 전에는 주소·학년·교습비를 함께 대조해 실제 등원 조건을 판단합니다.",
    ]
    paragraphs = [first_variants[seed % len(first_variants)]]
    if school_line:
        paragraphs.append(second_variants[(seed // len(first_variants)) % len(second_variants)])
    else:
        paragraphs.append(f"제공 자료에 {center['locality']} 학교 목록이 없어 학교명을 임의로 만들지 않았습니다. 상담 시 현재 학교의 시험 범위와 교재를 직접 확인해 학습 계획에 반영합니다.")
    paragraphs.append(third_variants[(seed // (len(first_variants) * len(second_variants))) % len(third_variants)])
    return (
        '<section class="subject-prose-section subject-local-context">'
        f'<h2>{escape(headings[seed % len(headings)])}</h2>'
        + "".join(paragraph_html(paragraph) for paragraph in paragraphs)
        + "</section>"
    )


def student_stage_context_html(center: dict, title: str) -> str:
    if CONFIG["kind"] != "student":
        return ""
    diagnostic_banks = {
        "고등": [
            "시험 범위는 알고 있지만 누적 단원의 빈틈 때문에 풀이가 자주 끊기는 경우",
            "내신 과제와 모의고사 학습을 같은 주에 배치해 공부 시간이 분산되는 경우",
            "정답은 맞혀도 근거 설명과 서술 과정이 불안정한 경우",
            "학기 중 진도와 방학 복습의 목표를 구분하지 못하는 경우",
            "과목별 점수 차이보다 시간 배분 실패가 반복되는 경우",
            "시험 직전 새 문제에 치우쳐 기존 오답을 다시 보지 못하는 경우",
            "학교 자료와 개인 교재의 우선순위가 매주 바뀌는 경우",
            "질문할 문제를 표시하지만 해결 과정을 기록하지 않는 경우",
            "수행평가 준비가 지필평가 복습 시간을 계속 밀어내는 경우",
            "강한 단원과 약한 단원의 공부 비중을 같은 방식으로 두는 경우",
            "풀이 속도는 빠르지만 검산과 근거 확인 시간이 부족한 경우",
            "계획표의 분량은 많지만 완료 기준이 구체적이지 않은 경우",
        ],
        "중등": [
            "학교 수업은 따라가지만 시험 범위를 혼자 정리하지 못하는 경우",
            "수행평가와 과제 마감이 겹치면 복습 순서를 놓치는 경우",
            "개념을 들으면 이해하지만 혼자 문제에 적용하기 어려운 경우",
            "오답을 지우고 다시 쓰지만 틀린 이유는 남기지 않는 경우",
            "시험 전 문제 수만 늘고 교과서 확인은 줄어드는 경우",
            "학년이 바뀐 뒤 과목별 공부 시간을 아직 조정하지 못한 경우",
            "숙제 완료와 실제 이해 정도가 다르게 나타나는 경우",
            "질문을 미루다가 시험 직전에 한꺼번에 해결하려는 경우",
            "학교 프린트와 개인 문제집의 연결 단원을 찾기 어려운 경우",
            "정답률은 비슷하지만 문제를 푸는 시간이 크게 흔들리는 경우",
            "평일 학습과 주말 보완의 역할이 구분되지 않는 경우",
            "부족한 과목을 오래 붙잡아 다른 과목 일정까지 밀리는 경우",
        ],
        "초등": [
            "설명을 들을 때는 알지만 혼자 시작하면 첫 단계에서 멈추는 경우",
            "학교 숙제와 학원 과제를 서로 다른 공부로 받아들이는 경우",
            "쉬운 문제도 여러 번 확인하느라 학습 시간이 길어지는 경우",
            "틀린 답을 고친 뒤 같은 유형을 다시 설명하지 못하는 경우",
            "읽기와 계산은 가능하지만 문장 조건을 놓치는 경우",
            "하교 뒤 공부 시작 시간이 날마다 달라지는 경우",
            "새 단원 진도보다 이전 개념의 복습이 먼저 필요한 경우",
            "도움을 받으면 풀지만 힌트 없이 재도전하기 어려운 경우",
            "과제를 끝내도 배운 내용을 짧게 말로 정리하지 않는 경우",
            "영어와 수학 중 편한 과목만 먼저 선택하는 경우",
            "문제 수에 비해 집중 시간이 짧아 작은 단위 계획이 필요한 경우",
            "틀리는 것을 피하려고 낯선 문제의 시도를 미루는 경우",
        ],
    }
    schedule_bank = [
        "학교 일정표에서 평가일과 과제 마감일을 먼저 표시한 뒤 복습 날짜를 역산합니다.",
        "필수 과제와 선택 과제를 나누고, 미완료분을 다음 날 무조건 더하지 않도록 재계획 기준을 정합니다.",
        "집중 시간이 필요한 과목과 짧은 반복이 필요한 과목을 다른 시간대에 배치합니다.",
        "수업 당일 확인, 사흘 뒤 재풀이, 일주일 뒤 회상의 세 시점을 구분해 기록합니다.",
        "평일에는 학교 진도 연결을, 주말에는 누적 오답과 설명 연습을 우선합니다.",
        "한 주 목표를 단원명·문항 수·완료 기준·다음 확인일로 나누어 적습니다.",
        "시험이 없는 주에도 짧은 누적 복습 시간을 남겨 직전 학습의 부담을 줄입니다.",
        "이동과 식사 시간을 제외한 실제 공부 가능 시간을 계산해 과목별 분량을 조정합니다.",
        "완료하지 못한 계획은 이유를 분류한 뒤 분량·난도·시작 시간을 하나씩 바꿉니다.",
        "학교 자료를 먼저 확인하고 개인 교재는 같은 개념의 보완 범위로 연결합니다.",
        "공부 시작 신호와 종료 기준을 정해 기분에 따라 시간이 달라지지 않게 합니다.",
        "새 진도와 복습을 같은 날 모두 늘리지 않고 주간 우선순위에 따라 한쪽을 조정합니다.",
    ]
    evidence_bank = [
        "변화는 점수 하나보다 도움 없이 다시 푼 문항과 설명할 수 있는 개념으로 확인합니다.",
        "오답 기록에는 정답뿐 아니라 처음 선택한 근거와 다음에 확인할 조건을 남깁니다.",
        "주간 피드백은 출석 여부보다 과제 완료율·질문 내용·재도전 결과를 함께 보여야 합니다.",
        "같은 유형의 두 번째 풀이에서 힌트가 얼마나 줄었는지를 비교하면 학습 지속성을 보기 쉽습니다.",
        "계획표와 실제 노트를 함께 보면 공부한 시간과 이해한 내용의 차이를 확인할 수 있습니다.",
        "시험 뒤에는 맞힌 문제도 근거가 불분명했다면 다시 설명하는 항목으로 분류합니다.",
        "학생이 스스로 정한 다음 행동과 교사가 확인할 날짜가 기록에 함께 남아야 합니다.",
        "학부모 피드백에는 결과보다 이번 주에 바꾼 방법과 다음 주 조정 이유가 포함되어야 합니다.",
        "질문의 수보다 질문이 개념·조건·풀이 중 어디에서 생겼는지를 구분해 봅니다.",
        "진단 결과는 고정 등급보다 현재 교재에서 혼자 수행할 수 있는 범위로 설명해야 합니다.",
        "과제량을 늘리기 전 기존 분량을 정해진 시간 안에 마쳤는지 먼저 확인합니다.",
        "재학습 효과는 바로 다음 풀이와 일정 시간이 지난 뒤의 풀이를 나누어 확인합니다.",
    ]
    question_bank = [
        "첫 상담에서는 이번 주에 줄일 일과 반드시 유지할 일을 각각 한 가지씩 물어보는 편이 좋습니다.",
        "학부모는 계획이 지켜지지 않았을 때 분량·난도·시간 중 무엇을 먼저 바꾸는지 질문해야 합니다.",
        "학생에게는 가장 어려운 과목보다 혼자 시작하기 어려운 장면을 구체적으로 말하게 합니다.",
        "상담 뒤에는 담당자, 확인 자료, 재점검 날짜가 기록으로 남는지 확인합니다.",
        "교재 이름보다 한 단원을 이해·적용·재현하는 절차가 어떻게 이어지는지 물어봅니다.",
        "시험 기간과 평상시의 과제량이 어떤 기준으로 달라지는지 사례를 들어 확인합니다.",
        "결석이나 학교 일정 변경이 생겼을 때 기존 계획을 조정하는 순서를 질문합니다.",
        "과목별 약점이 다를 때 주간 공부 시간을 같은 비율로 두지 않는 이유를 확인합니다.",
        "가정에서 확인할 항목이 학생의 자율성을 방해하지 않도록 역할을 구분해 달라고 요청합니다.",
        "첫 달 목표가 성적 표현이 아니라 관찰 가능한 학습 행동으로 제시되는지 살펴봅니다.",
        "학생이 질문을 하지 않을 때 교사가 막힌 지점을 어떻게 발견하는지 물어봅니다.",
        "현재 시간표로 실행하기 어려운 계획을 어떤 기준으로 줄이는지 확인합니다.",
    ]
    followup_bank = [
        "상담 뒤에는 진단에서 확인한 약점을 한꺼번에 바꾸기보다 다음 주에 다시 확인할 한 가지 행동부터 정하는 편이 현실적입니다.",
        "계획을 세울 때에는 교재 이름보다 어느 단원에서 무엇을 끝내고 어떤 기록으로 완료 여부를 판단할지 먼저 합의해야 합니다.",
        "학생에게 맞는 관리 방식인지 보려면 숙제 분량뿐 아니라 질문을 남기는 방법과 다음 수업에서 확인하는 절차도 함께 물어보는 것이 좋습니다.",
        "시험이 가까울수록 새 자료를 늘리기보다 이미 푼 문제에서 다시 틀리는 조건을 찾아 재풀이 순서를 정하는 편이 안정적입니다.",
        "주간 계획은 예상 시간이 아니라 실제 완료 시간을 남겨야 다음 계획에서 과목별 분량을 무리 없이 조절할 수 있습니다.",
        "학부모가 확인할 내용은 공부 시간의 총량보다 학생이 혼자 시작할 수 있었는지와 막힌 지점을 설명할 수 있었는지입니다.",
        "상담에서는 잘하는 단원과 어려운 단원을 함께 제시해야 보완 수업이 강점 과목의 시간을 지나치게 빼앗지 않도록 조정할 수 있습니다.",
        "과제를 끝내지 못한 날에는 의지만 평가하기보다 시작 시각, 문제 난도, 질문 대기 시간을 나누어 원인을 살펴보는 것이 필요합니다.",
        "오답은 정답을 옮겨 적는 기록이 아니라 처음 선택한 근거와 다시 풀 때 달라진 판단을 비교할 수 있어야 활용도가 높아집니다.",
        "진도 상담에서는 다음 단원으로 넘어갈 날짜와 함께 현재 단원을 다시 확인할 기준도 정해 두어야 학습 공백을 줄일 수 있습니다.",
        "학생이 질문을 어려워한다면 모르는 문제의 번호만 표시하는 단계부터 시작해 막힌 조건을 한 문장으로 적는 단계로 넓혀갈 수 있습니다.",
        "학습 상태는 한 번의 점수보다 최근 과제와 오답에서 같은 실수가 줄어드는지를 일정한 간격으로 비교할 때 더 정확히 볼 수 있습니다.",
        "수업 방식은 설명을 많이 듣는 형태인지 직접 풀고 피드백을 받는 형태인지 확인한 뒤 현재 학생의 필요한 연습과 맞춰야 합니다.",
        "계획표에는 공부할 내용만 적지 말고 완료 여부를 확인할 사람과 시점을 함께 표시해야 실행 기록으로 기능할 수 있습니다.",
        "시험 후 상담에서는 점수만 정리하지 말고 시간 부족, 개념 누락, 조건 해석 가운데 어떤 원인이 반복됐는지부터 분류하는 것이 좋습니다.",
        "새로운 학습 습관은 매일 여러 항목을 바꾸기보다 시작 시간이나 오답 재풀이처럼 관찰 가능한 한 항목부터 고정하는 편이 유지하기 쉽습니다.",
        "센터 정보를 비교할 때에는 안내된 학년과 과목을 확인하고 실제 수업 가능 여부와 시간표는 상담 시점에 다시 확인해야 합니다.",
    ]
    heading_bank = [
        f"{center['locality']} {AUDIENCE_LABEL}의 학습 장면을 상담 질문으로 바꾸는 법",
        f"{title} 상담에서 계획·실행·재확인을 연결하는 기준",
        f"{center['locality']} 학생의 주간 기록을 실제 조정에 활용하는 방법",
        f"학년 단계에 맞춘 {center['locality']} 학습 진단과 재점검 흐름",
        f"{center['locality']}에서 공부 시간과 학교 일정을 함께 보는 이유",
        f"결과보다 과정으로 확인하는 {title} 상담 기준",
    ]
    diagnostic = diagnostic_banks[LEVEL_LABEL][seeded_index(CATEGORY, center["slug"], "stage-diagnostic", modulo=12)]
    schedule = schedule_bank[seeded_index(CATEGORY, center["slug"], "stage-schedule", modulo=len(schedule_bank))]
    evidence = evidence_bank[seeded_index(CATEGORY, center["slug"], "stage-evidence", modulo=len(evidence_bank))]
    question = question_bank[seeded_index(CATEGORY, center["slug"], "stage-question", modulo=len(question_bank))]
    followup = followup_bank[seeded_index(CATEGORY, center["slug"], "stage-followup", modulo=len(followup_bank))]
    heading = heading_bank[seeded_index(CATEGORY, center["slug"], "stage-heading", modulo=len(heading_bank))]
    paragraphs = [
        f"{center['locality']} {AUDIENCE_LABEL} 상담에서는 {diagnostic}처럼 실제로 멈추는 장면을 먼저 확인해야 합니다. 과목명이나 점수만으로 판단하지 않고 최근 교재·과제·오답에서 그 장면이 반복되는지 살펴봅니다.",
        f"계획을 세울 때에는 학생이 실제로 사용할 수 있는 시간을 기준으로 해야 합니다. {schedule}",
        f"진행 결과는 다음 상담에서 다시 확인할 수 있는 자료로 남겨야 합니다. {evidence}",
        question,
        followup,
    ]
    paragraphs = [
        polish_phrase(align_subject_claims(paragraph, center), center, f"stage-{index}")
        for index, paragraph in enumerate(paragraphs)
    ]
    return (
        '<section class="subject-prose-section subject-stage-context">'
        f'<h2>{escape(heading)}</h2>'
        + "".join(paragraph_html(paragraph) for paragraph in paragraphs)
        + "</section>"
    )


def evidence_html(center: dict, title: str) -> str:
    region_line = " ".join(value for value in (center["region"], center["district"], center["locality"]) if value)
    tuition = (
        f'<a href="{escape(center["tuition"])}" target="_blank" rel="noopener noreferrer">교육지원청 등록 교습비 자료 확인</a>'
        if center["tuition"] else "제공 링크 없음 · 상담 시 확인"
    )
    registration = center["registration"] or "제공 자료 없음"
    return f'''<section class="section subject-evidence-section">
      <div class="subject-evidence-card">
        <div><p class="eyebrow">Information Basis</p><h2>{escape(title)} 정보 확인 기준</h2><p>센터명·주소·등록번호·학교 참고 목록은 제공 자료 범위에서 확인했습니다. 실제 수업 가능 학년과 과목, 시간표는 상담 시점에 다시 확인해야 합니다.</p></div>
        <dl>
          <div><dt>지역 기준</dt><dd>{escape(region_line)}</dd></div>
          <div><dt>센터 등록정보</dt><dd>{escape(registration)}</dd></div>
          <div><dt>교습비 근거</dt><dd>{tuition}</dd></div>
          <div><dt>페이지 반영일</dt><dd>{DATE_MODIFIED}</dd></div>
        </dl>
      </div>
    </section>'''


def center_payload(row: dict[str, str], slug: str) -> dict:
    all_schools = list(dict.fromkeys(
        school
        for school_field in ("타깃학교(초)", "타깃학교(중)", "타깃학교(고)")
        for school in split_school_names(field(row, school_field))
    ))
    map_name = map_source(row, slug)
    map_width, map_height = image_dimensions(ROOT / "assets" / "maps" / map_name)
    subject_grades = split_values(field(row, f"가능학년({SUBJECT_LABEL})")) if CONFIG["kind"] == "subject" else []
    if CONFIG["kind"] == "subject":
        grade_school_fields = {
            "초": "타깃학교(초)",
            "중": "타깃학교(중)",
            "고": "타깃학교(고)",
        }
        selected_school_fields = [
            school_field
            for prefix, school_field in grade_school_fields.items()
            if any(grade.startswith(prefix) for grade in subject_grades)
        ]
        selected_schools = list(dict.fromkeys(
            school
            for school_field in selected_school_fields
            for school in split_school_names(field(row, school_field))
        ))
    else:
        selected_schools = split_school_names(field(row, CONFIG["school_field"]))
    return {
        "locality": row["근처 수업가능 동네"],
        "slug": slug,
        "region": official_region(row),
        "source_region": row.get("지역", ""),
        "district": row.get("시or구", ""),
        "center": row.get("센터명", ""),
        "tuition": row.get("센터 교습비", ""),
        "office": row.get("교육지원청명칭", ""),
        "registration": row.get("교육지원청 등록번호", ""),
        "address": row.get("센터 주소", ""),
        "schools": selected_schools,
        "all_schools": all_schools,
        "grades": grade_intersection(row),
        "subjects": available_subjects(row),
        "map": map_name,
        "map_width": map_width,
        "map_height": map_height,
        "body_image": "seoul6839.webp" if row.get("지역") == "서울" else "local6839.webp",
    }


def management_scope(center: dict) -> str:
    if CONFIG["kind"] == "subject":
        if SUBJECT_LABEL != "영어":
            return f"초·중·고 {SUBJECT_LABEL} 학습관리"
        levels = [
            label
            for prefix, label in (("초", "초등"), ("중", "중등"), ("고", "고등"))
            if any(grade.startswith(prefix) for grade in center.get("grades", []))
        ]
        level_scope = "·".join(levels)
        return f"{level_scope + ' ' if level_scope else ''}{SUBJECT_LABEL} 학습관리"
    if CONFIG["kind"] == "student":
        return f"{LEVEL_LABEL} 학년 단계·학교 일정·학습 습관"
    return f"{LEVEL_LABEL} 영어·수학 학습관리"


def about_topics() -> list[str]:
    if CONFIG["kind"] == "subject":
        if SUBJECT_LABEL == "영어":
            return [CATEGORY_DISPLAY, "영어 어휘", "문장 구조", "독해 근거", "오답 관리", "복습 계획"]
        return [CATEGORY_DISPLAY, "수학 개념 이해", "문제 적용", "풀이 과정", "오답 관리", "복습 계획"]
    if CONFIG["kind"] == "student":
        return [CATEGORY_DISPLAY, f"{LEVEL_LABEL} 학년별 계획", "학교 학습 연결", "시간 관리", "학습 습관", "오답 재학습"]
    return [f"{LEVEL_LABEL} 영어", f"{LEVEL_LABEL} 수학", CATEGORY_DISPLAY, "내신 대비", "오답 관리"]


def same_level_combined_config() -> dict:
    for config in CONFIGS.values():
        if config["kind"] == "combined" and config["level"] == LEVEL_LABEL:
            return config
    raise ValueError(f"Missing combined config for {LEVEL_LABEL}")


def related_link_items(center: dict) -> list[dict[str, str]]:
    items = [
        {
            "name": f"{CATEGORY_DISPLAY} 전체 지역",
            "url": absolute_url("과목별학원", CATEGORY),
            "href": "../",
            "label": "현재 카테고리",
            "description": f"371개 동네의 {CATEGORY_DISPLAY} 안내를 살펴봅니다.",
        }
    ]
    if CONFIG["kind"] == "student":
        combined = same_level_combined_config()
        items.append({
            "name": f"{center['locality']} {combined['display']}",
            "url": absolute_url("과목별학원", combined["category"], center["slug"]),
            "href": f"../../{combined['category']}/{center['slug']}/",
            "label": "같은 학년 · 영수",
            "description": f"{LEVEL_LABEL} 영어·수학의 과목별 진단 기준을 확인합니다.",
        })
        peers = [config for config in CONFIGS.values() if config["kind"] == "student" and config["category"] != CATEGORY]
        for config in peers:
            items.append({
                "name": f"{center['locality']} {config['display']}",
                "url": absolute_url("과목별학원", config["category"], center["slug"]),
                "href": f"../../{config['category']}/{center['slug']}/",
                "label": "다른 학년 단계",
                "description": f"{config['audience']}의 학년별 계획과 학습 습관 기준을 비교합니다.",
            })
    items.extend([
        {
            "name": f"{center['locality']} 전국학원 안내",
            "url": absolute_url("전국센터", center["slug"]),
            "href": f"../../../전국센터/{center['slug']}/",
            "label": "지역 센터",
            "description": "해당 동네의 센터 위치와 전체 학습관리 기준을 확인합니다.",
        },
        {
            "name": "과목별학원",
            "url": absolute_url("과목별학원"),
            "href": "../../",
            "label": "전체 안내",
            "description": "학년과 과목에 따라 구분된 모든 지역 학습 안내를 살펴봅니다.",
        },
        {
            "name": "학습가이드",
            "url": absolute_url("학습가이드"),
            "href": "../../../학습가이드/",
            "label": "학습관리",
            "description": "진단, 플래너, 오답 재학습의 관리 흐름을 확인합니다.",
        },
    ])
    return items


def make_graph(page: dict, center: dict, representative: str) -> dict:
    sections = page["sections"]
    title = clean_text(sections["페이지타이틀"])
    description = meta_description(sections["메타설명"], title)
    summary = clean_text(sections["JSON-LD 요약"])
    faq = localized_faq(parse_faq(sections["FAQ"]), title, center["locality"])
    _, body_sections = parse_body(sections["본문"])
    canonical = absolute_url("과목별학원", CATEGORY, center["slug"])
    hub_url = absolute_url("과목별학원", CATEGORY)
    subject_url = absolute_url("과목별학원")
    home_url = DOMAIN + "/"
    webpage_id = canonical + "#webpage"
    center_key = normalize((center["center"] or center["locality"]) + "|" + (center["address"] or center["locality"]))
    org_id = DOMAIN + "/#center-" + hashlib.sha256(center_key.encode("utf-8")).hexdigest()[:12]
    article_id = canonical + "#article"
    service_id = canonical + "#service"
    breadcrumb_id = canonical + "#breadcrumb"
    faq_id = canonical + "#faq"
    itemlist_id = canonical + "#related"
    image_id = canonical + "#primaryimage"
    region_names = [value for value in (center["region"], center["district"], center["locality"]) if value]
    about = [{"@type": "Thing", "name": topic} for topic in about_topics()]
    mentions = [{"@type": "Place", "name": name} for name in region_names]
    mentions.extend({"@type": "School", "name": school} for school in center["schools"])
    has_part = [{"@type": "WebPageElement", "name": heading} for heading, _ in body_sections]
    has_part.extend(
        [
            {"@type": "WebPageElement", "name": "수업·상담 핵심정보"},
            {"@type": "WebPageElement", "name": "본문 안내 이미지"},
            {"@type": "WebPageElement", "name": "센터 지도"},
            {"@type": "WebPageElement", "name": "자주 묻는 질문"},
            {"@type": "WebPageElement", "name": "학부모 상담 관점"},
            {"@type": "WebPageElement", "name": f"{center['locality']} 지역 학습 조건"},
            {"@type": "WebPageElement", "name": "정보 확인 기준"},
            {"@type": "WebPageElement", "name": "관련 학습 안내"},
        ]
    )
    offer = {
        "@type": "Offer",
        "name": f"{title} 상담 및 학습관리",
        "itemOffered": {"@type": "Service", "name": title, "serviceType": management_scope(center)},
    }
    if center["tuition"]:
        offer["url"] = center["tuition"]
    organization = {
        "@type": ["EducationalOrganization", "LocalBusiness"],
        "@id": org_id,
        "name": center["center"] or title,
        "url": absolute_url("전국센터", center["slug"]),
        "image": representative,
        "telephone": PHONE,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": center["address"],
            "addressRegion": center["region"],
            "addressLocality": center["district"],
            "addressCountry": "KR",
        },
        "areaServed": {"@type": "Place", "name": center["locality"]},
        "knowsAbout": about_topics(),
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+82-10-6839-8283",
            "contactType": "학습 상담",
            "availableLanguage": "Korean",
        },
    }
    if center["registration"]:
        organization["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "교육지원청 등록번호",
            "value": center["registration"],
        }
    if center["grades"]:
        organization["educationalLevel"] = center["grades"]
        organization["makesOffer"] = [offer]
    graph = [
        {
            "@type": "WebPage",
            "@id": webpage_id,
            "url": canonical,
            "name": title,
            "description": description,
            "inLanguage": "ko-KR",
            "dateModified": DATE_MODIFIED,
            "primaryImageOfPage": {"@id": image_id},
            "breadcrumb": {"@id": breadcrumb_id},
            "mainEntity": {"@id": service_id},
            "about": about,
            "mentions": mentions,
            "hasPart": has_part,
        },
        {"@type": "ImageObject", "@id": image_id, "url": representative, "caption": f"{title} {PUBLIC_SITE_NAME} 대표"},
        organization,
        {
            "@type": "BreadcrumbList",
            "@id": breadcrumb_id,
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "홈", "item": home_url},
                {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": subject_url},
                {"@type": "ListItem", "position": 3, "name": CATEGORY_DISPLAY, "item": hub_url},
                {"@type": "ListItem", "position": 4, "name": title, "item": canonical},
            ],
        },
        {
            "@type": "Article",
            "@id": article_id,
            "headline": title,
            "description": description,
            "abstract": summary,
            "image": [representative, absolute_url("assets", "centers", "common", center["body_image"]).rstrip("/")],
            "inLanguage": "ko-KR",
            "datePublished": DATE_PUBLISHED,
            "dateModified": DATE_MODIFIED,
            "author": {"@id": org_id},
            "publisher": {"@type": "EducationalOrganization", "@id": DOMAIN + "/#organization", "name": SITE_NAME, "url": home_url},
            "sourceOrganization": {"@id": org_id},
            "mainEntityOfPage": {"@id": webpage_id},
            "articleSection": [heading for heading, _ in body_sections],
            "about": about,
            "mentions": mentions,
            "hasPart": has_part,
            "isBasedOn": {
                "@type": "CreativeWork",
                "name": f"{center['locality']} 센터 제공 정보",
                "dateModified": DATE_MODIFIED,
            },
            "citation": ([{
                "@type": "WebPage",
                "name": "교육지원청 등록 교습비 자료",
                "url": center["tuition"],
            }] if center["tuition"] else []),
        },
        {
            "@type": "Service",
            "@id": service_id,
            "name": f"{title} 학습관리" if center["grades"] else f"{center['locality']} {SUBJECT_LABEL + ' ' if CONFIG['kind'] == 'subject' else ''}수업 가능 여부 상담",
            "serviceType": management_scope(center) if center["grades"] else f"{SUBJECT_LABEL + ' ' if CONFIG['kind'] == 'subject' else '학년별 '}수업 가능 여부 상담",
            "description": summary,
            "provider": {"@id": org_id},
            "areaServed": {"@type": "Place", "name": center["locality"]},
            "audience": {"@type": "EducationalAudience", "educationalRole": "student", "audienceType": audience_for_center(center)},
            "about": about,
            "mentions": mentions,
            **({"makesOffer": [offer]} if center["grades"] else {}),
        },
        {
            "@type": "FAQPage",
            "@id": faq_id,
            "mainEntity": [
                {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
                for question, answer in faq
            ],
        },
        {
            "@type": "ItemList",
            "@id": itemlist_id,
            "name": f"{center['locality']} 관련 학습 안내",
            "itemListElement": [
                {"@type": "ListItem", "position": index, "name": item["name"], "url": item["url"]}
                for index, item in enumerate(related_link_items(center), 1)
            ],
        },
    ]
    return {"@context": "https://schema.org", "@graph": graph}


def render_info_rows(center: dict) -> str:
    grade_html = "".join(f"<span>{escape(grade)}</span>" for grade in center["grades"])
    school_html = "".join(f"<span>{escape(school)}</span>" for school in center["schools"])
    rows = [
        f"<div><dt>지역</dt><dd>{escape(' '.join(v for v in (center['region'], center['district'], center['locality']) if v))}</dd></div>",
        f"<div><dt>센터 기준</dt><dd>{escape(center['center'] or center['locality'] + ' 학습센터')}</dd></div>",
        f"<div><dt>제공 주소</dt><dd>{escape(center['address'] or '상담 시 확인')}</dd></div>",
        f"<div><dt>{'센터 전체 수업 가능 학년' if CONFIG['kind'] == 'student' else f'{SUBJECT_LABEL} 가능 학년' if CONFIG['kind'] == 'subject' else '영어·수학 가능 학년'}</dt><dd><div class=\"subject-tag-list\">{grade_html or '<span>상담 시 확인</span>'}</div></dd></div>",
    ]
    if CONFIG["kind"] == "student" and center["subjects"]:
        subjects_html = "".join(f"<span>{escape(subject)}</span>" for subject in center["subjects"])
        rows.append(f"<div><dt>{LEVEL_LABEL} 제공 과목 참고</dt><dd><div class=\"subject-tag-list\">{subjects_html}</div></dd></div>")
    if center["registration"]:
        rows.append(f"<div><dt>교육지원청 등록번호</dt><dd>{escape(center['registration'])}</dd></div>")
    if center["schools"]:
        rows.append(f"<div><dt>제공 학교 참고</dt><dd><div class=\"subject-tag-list\">{school_html}</div></dd></div>")
    if center["tuition"]:
        rows.append(
            f'<div class="subject-tuition-row"><dt>센터 교습비</dt><dd><a class="subject-tuition-link" href="{escape(center["tuition"])}" target="_blank" rel="noopener noreferrer">센터별 교습비 안내 <span aria-hidden="true">↗</span></a><small>등록된 센터별 교습비 자료를 새 창에서 확인합니다.</small></dd></div>'
        )
    return "".join(rows)


def render_page(page: dict, center: dict, representative: str) -> str:
    sections = page["sections"]
    title = clean_text(sections["페이지타이틀"])
    description = meta_description(sections["메타설명"], title)
    summary = clean_text(sections["JSON-LD 요약"])
    intro, body_sections = parse_body(sections["본문"])
    faq = localized_faq(parse_faq(sections["FAQ"]), title, center["locality"])
    review_note, reviews = parse_review(sections["학부모후기"])
    canonical = absolute_url("과목별학원", CATEGORY, center["slug"])
    graph = make_graph(page, center, representative)
    body_html = local_context_html(center, title) + student_stage_context_html(center, title) + "".join(
        f'<section class="subject-prose-section"><h2>{escape(heading)}</h2>{"".join(paragraph_html(paragraph) for paragraph in paragraphs)}</section>'
        for heading, paragraphs in body_sections
    )
    faq_html = "".join(
        f'<details class="subject-faq-item"{" open" if index == 0 else ""}><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>'
        for index, (question, answer) in enumerate(faq)
    )
    review_html = "".join(f'<blockquote class="subject-review-item">{escape(review)}</blockquote>' for review in reviews)
    locality = center["locality"]
    region_line = " ".join(v for v in (center["region"], center["district"], locality) if v)
    alt_base = f"{title} {PUBLIC_SITE_NAME}"
    info_rows = render_info_rows(center)
    related_cards = "".join(
        f'<a class="related-link-card" href="{escape(item["href"])}"><span>{escape(item["label"])}</span><b>{escape(item["name"])}</b><em>{escape(item["description"])}</em></a>'
        for item in related_link_items(center)
    )
    hero_scope = (
        "학년 단계·학교 일정·학습 습관" if CONFIG["kind"] == "student" else
        ("어휘·구문·독해·복습" if SUBJECT_LABEL == "영어" else "개념·풀이·오답·복습") if CONFIG["kind"] == "subject" else
        "진단·내신·오답 관리"
    )
    audience = audience_for_center(center)
    subject_reading_prompt = (
        "영어에서 막히는 어휘·문장 구조·독해 단서와 최근 오답을 기록합니다."
        if SUBJECT_LABEL == "영어" else
        "수학에서 막히는 풀이 단계와 최근 오답을 기록합니다."
    )
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | {PUBLIC_SITE_NAME}</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(title)} | {PUBLIC_SITE_NAME}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{escape(representative)}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="../../../assets/favicon.png">
  <link rel="stylesheet" href="../../../assets/site.css">
  <link rel="stylesheet" href="../../../assets/site-modern.css">
  <script type="application/ld+json">{json.dumps(graph, ensure_ascii=False, separators=(",", ":"))}</script>
</head>
<body class="subject-academy-page">
  <a class="skip-link" href="#main-content">본문 바로가기</a>
  <header class="site-header"><div class="header-inner">
    <a class="brand" href="../../../"><span class="brand-mark" aria-hidden="true">W</span><span>{SITE_NAME}</span></a>
    <nav class="nav" aria-label="상단 메뉴"><a href="../../../">홈</a><a href="../../../학습가이드/">학습가이드</a><a href="../../../상담문의/">상담문의</a><a href="../../" aria-current="page">과목별학원</a><a href="../../../전국센터/">전국학원</a></nav>
    <a class="header-cta" href="{FORM_URL}" target="_blank" rel="noopener">상담 신청</a>
  </div></header>
  <main id="main-content">
    <section class="local-hero subject-local-hero">
      <nav class="mini-breadcrumb" aria-label="현재 위치"><a href="../../../">홈</a><span>›</span><a href="../../">과목별학원</a><span>›</span><a href="../">{CATEGORY_DISPLAY}</a><span>›</span><strong>{escape(title)}</strong></nav>
      <p class="eyebrow">{escape(EYEBROW_LABEL)}</p>
      <h1>{escape(title)}</h1>
      <p class="lead">{escape(description)}</p>
      <div class="hero-points"><span>{escape(region_line)}</span><span>{escape(audience)} 학습관리</span><span>{escape(hero_scope)}</span></div>
    </section>

    <section class="section subject-summary-section">
      <div class="subject-summary-grid">
        <article class="subject-answer-card"><p class="eyebrow">30초 핵심 안내</p><h2>{escape(title)} 선택 전 확인할 기준</h2><p>{escape(summary)}</p></article>
        <aside class="subject-info-card"><h2>수업·상담 핵심정보</h2><dl>{info_rows}</dl></aside>
      </div>
    </section>

    <section class="local-media-section subject-media-section">
      <div class="local-media-card">
        <img src="{escape(representative)}" alt="{escape(alt_base)} 대표" style="display:none;">
        <p class="local-media-label">수업 안내 이미지</p>
        <picture><source media="(max-width: 680px)" srcset="../../../assets/centers/common/{center['body_image'].replace('.webp', '-mobile.webp')}"><img src="../../../assets/centers/common/{center['body_image']}" alt="{escape(alt_base)} 본문" loading="lazy" decoding="async" width="918" height="16116"></picture>
      </div>
      <div class="local-media-card"><p class="local-media-label">센터 위치 안내</p><img src="../../../assets/maps/{escape(center['map'])}" alt="{escape(alt_base)} 지도" loading="lazy" decoding="async" width="{center['map_width']}" height="{center['map_height']}"></div>
    </section>

    <section class="section subject-article-section">
      <div class="subject-article-layout">
        <article class="subject-main-article"><div class="subject-intro-answer"><p>{escape(intro)}</p></div>{body_html}</article>
        <aside class="subject-reading-guide"><p class="eyebrow">Reading Guide</p><h2>상담 전에 확인하세요</h2><ol><li>{'현재 학년의 학교 일정과 공부 시간을 정리합니다.' if CONFIG['kind'] == 'student' else subject_reading_prompt if CONFIG['kind'] == 'subject' else '영어와 수학의 막히는 원인을 따로 기록합니다.'}</li><li>학교 시험 범위와 현재 교재를 함께 준비합니다.</li><li>수업·과제·오답의 다음 확인일을 묻습니다.</li><li>주소와 교습비는 제공된 최신 자료로 확인합니다.</li></ol></aside>
      </div>
    </section>

    {evidence_html(center, title)}

    <section class="section subject-faq-section"><div class="section-head center"><p class="eyebrow">FAQ</p><h2>{escape(title)} 자주 묻는 질문</h2></div><div class="subject-faq-list">{faq_html}</div></section>
    <section class="section subject-review-section"><div class="subject-review-card"><p class="eyebrow">Parent Perspective</p><h2>{escape(title)} 학부모 상담 관점</h2><p class="subject-review-note">{escape(review_note)}</p><div class="subject-review-list">{review_html}</div></div></section>

    <section class="section related-links-section"><div class="section-head center"><p class="eyebrow">Related Pages</p><h2>{escape(locality)} 관련 학습 안내</h2><p class="lead">같은 지역의 학년별·과목별 안내와 확인된 센터 정보를 연결했습니다.</p></div><div class="related-link-grid">{related_cards}</div></section>
  </main>
  <footer class="footer"><div class="footer-inner"><div><strong>{SITE_NAME}</strong><br>초중고 영어·수학·국어 학습관리 안내</div><div>상담 전화 <a href="tel:{PHONE_LINK}">{PHONE}</a></div></div></footer>
  <aside class="floating-actions" aria-label="빠른 상담 버튼"><a href="tel:{PHONE_LINK}">전화문의</a><a href="{SMS_URL}" target="_blank" rel="noopener">문자문의</a><a href="{FORM_URL}" target="_blank" rel="noopener">상담신청</a></aside>
</body>
</html>
'''


def hub_graph(pages: list[tuple[dict, dict]]) -> dict:
    canonical = absolute_url("과목별학원", CATEGORY)
    if CONFIG["kind"] == "student":
        hub_description = f"371개 동네별 {AUDIENCE_LABEL}의 학년 단계, 학교 일정, 공부 시간과 학습 습관 기준을 확인할 수 있는 지역 허브입니다."
    elif CONFIG["kind"] == "subject":
        subject_process = "어휘·문장 구조·독해·복습" if SUBJECT_LABEL == "영어" else "개념 이해·풀이 과정·오답·복습"
        hub_description = f"371개 동네별 {CATEGORY_DISPLAY} 선택 기준과 {subject_process} 및 센터 정보를 확인할 수 있는 지역 허브입니다."
    else:
        hub_description = f"371개 동네별 {LEVEL_LABEL} 영어·수학 학원 선택 기준과 센터 정보를 확인할 수 있는 지역 허브입니다."
    items = [
        {"@type": "ListItem", "position": index + 1, "name": clean_text(page["sections"]["페이지타이틀"]), "url": absolute_url("과목별학원", CATEGORY, center["slug"])}
        for index, (page, center) in enumerate(pages)
    ]
    if CONFIG["kind"] == "student":
        faq_items = [
            (f"{CATEGORY_DISPLAY}을 비교할 때 무엇을 먼저 확인해야 하나요?", f"{AUDIENCE_LABEL}의 현재 학년과 학교 일정, 과목별 취약 원인, 실제 공부 시간과 복습 습관을 함께 확인해야 합니다."),
            ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·해당 학교급·주소 자료를 바탕으로 학년 단계, 상담 질문, 과제와 오답 관리 기준을 정리했습니다."),
        ]
    elif CONFIG["kind"] == "subject":
        if SUBJECT_LABEL == "영어":
            faq_items = [
                ("영어학원을 비교할 때 무엇을 먼저 확인해야 하나요?", "현재 학년보다 먼저 어휘 인출, 문장 구조 이해, 독해 근거 확인과 오답 복습이 어떤 순서로 이어지는지 확인해야 합니다."),
                ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·영어 가능 학년·학교·주소 자료와 지역별 학습 안내를 바탕으로 상담 질문과 복습 기준을 정리했습니다."),
            ]
        else:
            faq_items = [
                ("수학학원을 비교할 때 무엇을 먼저 확인해야 하나요?", "현재 학년보다 먼저 개념 설명, 문제 적용, 풀이 과정과 오답 재확인이 어떤 순서로 이어지는지 확인해야 합니다."),
                ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·수학 가능 학년·학교·주소 자료와 개별 원고를 바탕으로 상담 질문과 복습 기준을 정리했습니다."),
            ]
    else:
        faq_items = [
            (f"{CATEGORY_DISPLAY}을 비교할 때 무엇을 먼저 확인해야 하나요?", "영어와 수학을 같은 기준으로 묶지 말고, 영어는 어휘·문법·독해를, 수학은 개념·유형·풀이·오답을 따로 진단하는지 확인해야 합니다."),
            ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·학교·주소 자료와 개별 원고를 바탕으로 수업 대상, 상담 질문, 내신과 오답 관리 기준을 정리했습니다."),
        ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": canonical + "#webpage", "url": canonical, "name": f"{CATEGORY_DISPLAY} 지역 안내", "description": hub_description, "inLanguage": "ko-KR", "dateModified": DATE_MODIFIED, "breadcrumb": {"@id": canonical + "#breadcrumb"}, "mainEntity": {"@id": canonical + "#itemlist"}, "about": [{"@type": "Thing", "name": topic} for topic in about_topics()]},
            {"@type": "BreadcrumbList", "@id": canonical + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": absolute_url("과목별학원")}, {"@type": "ListItem", "position": 3, "name": CATEGORY_DISPLAY, "item": canonical}]},
            {"@type": "ItemList", "@id": canonical + "#itemlist", "name": f"동네별 {CATEGORY_DISPLAY} 안내", "numberOfItems": len(items), "itemListElement": items},
            {"@type": "FAQPage", "@id": canonical + "#faq", "mainEntity": [
                {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
                for question, answer in faq_items
            ]},
        ],
    }


def render_hub(pages: list[tuple[dict, dict]]) -> str:
    canonical = absolute_url("과목별학원", CATEGORY)
    if CONFIG["kind"] == "student":
        meta = f"371개 동네별 {CATEGORY_DISPLAY} 선택 기준을 학년 단계, 학교 일정, 공부 시간, 과제·오답과 학습 습관 중심으로 정리했습니다."
        lead = f"{AUDIENCE_LABEL} 학습은 현재 학년의 학교 일정과 과목별 약점, 실제 공부 시간을 함께 보아야 합니다. 아래에서 지역을 선택해 학생 상황별 안내와 확인된 센터 정보를 살펴보세요."
        guide_title = f"{AUDIENCE_LABEL}에게 필요한 것은 과목 수보다 실행 순서입니다"
        guide_text = f"학교 진도와 평가 일정을 확인하고, 과목별 취약 원인을 나눈 뒤 과제·오답·복습이 가능한 주간 계획으로 조정합니다. 상담에서는 학년 단계와 공부 습관이 실제 기록으로 이어지는지 확인하세요."
        guide_rows = (("학년 단계", AUDIENCE_LABEL), ("핵심 기준", "학교 일정 · 공부 시간"), ("학습 흐름", "진단 · 과제 · 오답 · 복습"), ("사실 정보", "센터 · 학교 · 주소 제공 자료"))
        visible_faq = (
            (f"{CATEGORY_DISPLAY}을 비교할 때 무엇을 먼저 확인해야 하나요?", f"{AUDIENCE_LABEL}의 현재 학년과 학교 일정, 과목별 취약 원인, 실제 공부 시간과 복습 습관을 함께 확인해야 합니다."),
            ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·해당 학교급·주소 자료를 바탕으로 학년 단계, 상담 질문, 과제와 오답 관리 기준을 정리했습니다."),
        )
    elif CONFIG["kind"] == "subject":
        if SUBJECT_LABEL == "영어":
            meta = "371개 동네별 영어학원 선택 기준을 지역과 시군구별로 정리했습니다. 영어 가능 학년, 어휘·구문·독해·복습과 센터 정보를 확인하세요."
            lead = "영어는 학년명이나 진도보다 학생이 어휘를 인출하고 문장 구조와 독해 근거를 설명한 뒤 오답을 다시 확인하는 흐름을 함께 보아야 합니다. 아래에서 지역을 선택해 지역별 학습 안내와 확인된 센터 정보를 살펴보세요."
            guide_title = "영어는 진도보다 이해 근거와 누적 복습을 봅니다"
            guide_text = "현재 교재와 최근 오답을 바탕으로 어휘 인출, 문장 구조, 독해 근거, 문법 적용 중 어디에서 막히는지 나눕니다. 상담에서는 첫 목표와 완료 기준, 다음 점검 날짜가 구체적인지 확인하세요."
            guide_rows = (("지역", "13개 광역권 · 371개 동네"), ("대상", "센터별 영어 가능 학년 기준"), ("내용", "지역별 안내 · 센터 · 학교 · 주소 정보"), ("관리", "어휘 · 구문 · 독해 · 복습"))
            visible_faq = (
                ("영어학원을 비교할 때 무엇을 먼저 확인해야 하나요?", "현재 학년보다 먼저 어휘 인출, 문장 구조 이해, 독해 근거 확인과 오답 복습이 어떤 순서로 이어지는지 확인해야 합니다."),
                ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·영어 가능 학년·학교·주소 자료와 지역별 학습 안내를 바탕으로 상담 질문과 복습 기준을 정리했습니다."),
            )
        else:
            meta = "371개 동네별 수학학원 선택 기준을 지역과 시군구별로 정리했습니다. 수학 가능 학년, 개념·풀이·오답·복습과 센터 정보를 확인하세요."
            lead = "수학은 학년명이나 진도보다 학생이 개념을 설명하고 문제에 적용하는 과정, 풀이 오류를 다시 확인하는 흐름을 함께 보아야 합니다. 아래에서 지역을 선택해 개별 원고와 확인된 센터 정보를 살펴보세요."
            guide_title = "수학은 정답보다 풀이 과정과 재확인 기준을 봅니다"
            guide_text = "현재 교재와 최근 오답을 바탕으로 개념 이해, 조건 해석, 식 세우기, 계산과 검산 중 어디에서 막히는지 나눕니다. 상담에서는 첫 목표와 완료 기준, 다음 점검 날짜가 구체적인지 확인하세요."
            guide_rows = (("지역", "13개 광역권 · 371개 동네"), ("대상", "센터별 수학 가능 학년 기준"), ("내용", "개별 원고 · 센터 · 학교 · 주소 정보"), ("관리", "개념 · 풀이 · 오답 · 복습"))
            visible_faq = (
                ("수학학원을 비교할 때 무엇을 먼저 확인해야 하나요?", "현재 학년보다 먼저 개념 설명, 문제 적용, 풀이 과정과 오답 재확인이 어떤 순서로 이어지는지 확인해야 합니다."),
                ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·수학 가능 학년·학교·주소 자료와 개별 원고를 바탕으로 상담 질문과 복습 기준을 정리했습니다."),
            )
    else:
        meta = f"371개 동네별 {LEVEL_LABEL} 영어·수학 학원 선택 기준을 지역과 시군구별로 정리했습니다. 센터 정보, 학교 내신, 과목별 진단과 오답 관리 기준을 확인하세요."
        lead = f"{LEVEL_LABEL} 영어와 수학은 학습 방식이 다르기 때문에 과목별 진단과 주간 계획을 따로 세우되, 학교 시험 일정과 전체 학습량은 함께 조정해야 합니다. 아래에서 지역을 선택해 개별 원고와 확인된 센터 정보를 살펴보세요."
        guide_title = "영어와 수학을 같은 방식으로 관리하지 않습니다"
        guide_text = "영어는 어휘·구문·독해·서술형의 누적 상태를, 수학은 개념 이해·유형 적용·풀이 과정·오답 원인을 나누어 확인합니다. 상담에서는 각 과목의 우선순위와 재점검 날짜가 구체적으로 남는지 살펴보세요."
        guide_rows = (("지역", "13개 광역권 · 371개 동네"), ("대상", "센터별 제공 가능 학년 기준"), ("내용", "개별 원고 · 센터 · 학교 · 주소 정보"), ("관리", "진단 · 내신 · 과제 · 오답 재학습"))
        visible_faq = (
            (f"{CATEGORY_DISPLAY}을 비교할 때 무엇을 먼저 확인해야 하나요?", "영어와 수학을 같은 기준으로 묶지 말고, 영어는 어휘·문법·독해를, 수학은 개념·유형·풀이·오답을 따로 진단하는지 확인해야 합니다."),
            ("지역별 페이지에는 어떤 정보가 있나요?", "제공된 지역·센터·학교·주소 자료와 개별 원고를 바탕으로 수업 대상, 상담 질문, 내신과 오답 관리 기준을 정리했습니다."),
        )
    regions: dict[str, dict[str, list[tuple[dict, dict]]]] = {}
    for page, center in pages:
        regions.setdefault(center["region"], {}).setdefault(center["district"], []).append((page, center))
    region_html = []
    for region, districts in regions.items():
        district_html = []
        for district, entries in districts.items():
            links = "".join(
                f'<a class="subject-locality-link" href="{escape(center["slug"])}/" data-search="{escape(" ".join((region, district, center["locality"], center["center"], clean_text(page["sections"]["페이지타이틀"]))))}"><b>{escape(center["locality"])}</b><span>{CATEGORY_DISPLAY}</span><i aria-hidden="true">→</i></a>'
                for page, center in entries
            )
            district_html.append(f'<section class="subject-district-block"><div class="subject-district-heading"><h3>{escape(district or region)}</h3><span>{len(entries)}곳</span></div><div class="subject-locality-grid">{links}</div></section>')
        opened = " open" if not region_html else ""
        region_count = sum(len(v) for v in districts.values())
        region_html.append(f'<details class="subject-region-block" data-region{opened}><summary class="subject-region-heading"><span><small>광역지역</small>{escape(region)}</span><strong>{region_count}개 동네<i aria-hidden="true"></i></strong></summary><div class="subject-region-content">{"".join(district_html)}</div></details>')
    graph = hub_graph(pages)
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{CATEGORY_DISPLAY} 지역 찾기 | {PUBLIC_SITE_NAME}</title>
<meta name="description" content="{escape(meta)}">
<meta name="robots" content="index,follow"><meta property="og:type" content="website"><meta property="og:title" content="{CATEGORY_DISPLAY} 지역 찾기 | {PUBLIC_SITE_NAME}"><meta property="og:description" content="{escape(meta)}"><meta property="og:url" content="{canonical}"><link rel="canonical" href="{canonical}"><link rel="icon" href="../../assets/favicon.png"><link rel="stylesheet" href="../../assets/site.css"><link rel="stylesheet" href="../../assets/site-modern.css"><script type="application/ld+json">{json.dumps(graph, ensure_ascii=False, separators=(",", ":"))}</script></head>
<body class="subject-hub-page"><a class="skip-link" href="#main-content">본문 바로가기</a><header class="site-header"><div class="header-inner"><a class="brand" href="../../"><span class="brand-mark" aria-hidden="true">W</span><span>{SITE_NAME}</span></a><nav class="nav" aria-label="상단 메뉴"><a href="../../">홈</a><a href="../../학습가이드/">학습가이드</a><a href="../../상담문의/">상담문의</a><a href="../" aria-current="page">과목별학원</a><a href="../../전국센터/">전국학원</a></nav><a class="header-cta" href="{FORM_URL}" target="_blank" rel="noopener">상담 신청</a></div></header>
<main id="main-content"><section class="page-hero subject-hub-hero"><nav class="mini-breadcrumb" aria-label="현재 위치"><a href="../../">홈</a><span>›</span><a href="../">과목별학원</a><span>›</span><strong>{CATEGORY_DISPLAY}</strong></nav><p class="eyebrow">{escape(EYEBROW_LABEL)}</p><h1>동네별 {CATEGORY_DISPLAY}</h1><p class="lead">{escape(lead)}</p><div class="hero-points"><span>371개 동네</span><span>학생 상황별 안내</span><span>제공 자료 기반</span></div></section>
<section class="section subject-hub-intro"><div class="subject-summary-grid"><article class="subject-answer-card"><p class="eyebrow">Selection Guide</p><h2>{escape(guide_title)}</h2><p>{escape(guide_text)}</p></article><aside class="subject-info-card"><h2>페이지 구성</h2><dl>{''.join(f'<div><dt>{escape(key)}</dt><dd>{escape(value)}</dd></div>' for key, value in guide_rows)}</dl></aside></div></section>
<section class="section subject-directory-section"><div class="section-head center"><p class="eyebrow">Local Directory</p><h2>{CATEGORY_DISPLAY} 지역 선택</h2><p class="lead">광역지역을 펼쳐 시군구와 동네를 차례로 확인하거나, 검색창에서 바로 찾아보세요.</p></div><div class="subject-directory-overview" aria-label="지역 안내 요약"><div><strong>{len(regions)}</strong><span>광역지역</span></div><div><strong>{len(pages)}</strong><span>동네 안내</span></div><p>처음에는 한 지역만 열어 두어 목록을 간결하게 정리했습니다.</p></div><div class="subject-directory-tools"><label class="subject-search"><span>지역 검색</span><input id="subject-local-search" type="search" placeholder="서울 · 강동구 · 명일동" autocomplete="off"></label><div class="subject-directory-actions"><button type="button" id="subject-expand-all">모두 펼치기</button><button type="button" id="subject-collapse-all">모두 접기</button></div></div><p class="subject-search-result" id="subject-search-result" aria-live="polite">전체 {len(pages)}개 동네</p><div class="subject-region-list">{"".join(region_html)}</div></section>
<section class="section"><div class="section-head center"><p class="eyebrow">FAQ</p><h2>{CATEGORY_DISPLAY} 자주 묻는 질문</h2></div><div class="faq">{''.join(f'<details{" open" if index == 0 else ""}><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>' for index, (question, answer) in enumerate(visible_faq))}</div></section></main>
<footer class="footer"><div class="footer-inner"><div><strong>{SITE_NAME}</strong><br>초중고 영어·수학·국어 학습관리 안내</div><div>상담 전화 <a href="tel:{PHONE_LINK}">{PHONE}</a></div></div></footer><aside class="floating-actions" aria-label="빠른 상담 버튼"><a href="tel:{PHONE_LINK}">전화문의</a><a href="{SMS_URL}" target="_blank" rel="noopener">문자문의</a><a href="{FORM_URL}" target="_blank" rel="noopener">상담신청</a></aside>
<script>(function(){{var input=document.getElementById('subject-local-search'),result=document.getElementById('subject-search-result'),links=[].slice.call(document.querySelectorAll('.subject-locality-link')),regions=[].slice.call(document.querySelectorAll('[data-region]')),expand=document.getElementById('subject-expand-all'),collapse=document.getElementById('subject-collapse-all');function update(){{var query=(input.value||'').trim().toLowerCase(),shown=0;links.forEach(function(link){{var haystack=(link.getAttribute('data-search')||link.textContent).toLowerCase(),match=!query||haystack.indexOf(query)>-1;link.hidden=!match;if(match)shown++;}});document.querySelectorAll('.subject-district-block').forEach(function(block){{block.hidden=!block.querySelector('.subject-locality-link:not([hidden])');}});regions.forEach(function(block){{block.hidden=!block.querySelector('.subject-locality-link:not([hidden])');if(query&&!block.hidden)block.open=true;}});result.textContent=query?'검색 결과 '+shown+'개':'전체 {len(pages)}개 동네';}}input.addEventListener('input',update);expand.addEventListener('click',function(){{regions.forEach(function(block){{if(!block.hidden)block.open=true;}});}});collapse.addEventListener('click',function(){{regions.forEach(function(block){{block.open=false;}});}});}})();</script></body></html>'''


def update_subject_root() -> None:
    path = ROOT / "과목별학원" / "index.html"
    source = path.read_text(encoding="utf-8")
    cards = []
    for config in CONFIGS.values():
        category = config["category"]
        if not (ROOT / "과목별학원" / category / "index.html").exists():
            continue
        icon = "학년" if config["kind"] == "student" else config.get("subject", "과목") if config["kind"] == "subject" else "E+M"
        cards.append(
            f'<a class="subject-category-card" href="{category}/"><span class="subject-category-icon">{icon}</span><span><small>{config["card_small"]}</small><strong>{config["display"]}</strong><em>{config["card_description"]}</em></span><b aria-hidden="true">→</b></a>'
        )
    block = f'''<!-- SUBJECT-CATEGORY-CARDS-START -->
    <section class="section subject-category-section">
      <div class="section-head center"><p class="eyebrow">Published Guide</p><h2>현재 확인할 수 있는 과목별 안내</h2><p class="lead">개별 원고와 확인된 센터 자료를 바탕으로 작성한 지역 페이지입니다.</p></div>
      <div class="subject-category-grid">{"".join(cards)}</div>
    </section>
<!-- SUBJECT-CATEGORY-CARDS-END -->'''
    pattern = re.compile(
        r"\s*<!-- (?:HIGH-COMBINED|SUBJECT-CATEGORY-CARDS)-START -->.*?<!-- (?:HIGH-COMBINED|SUBJECT-CATEGORY-CARDS)-END -->",
        re.DOTALL,
    )
    source = pattern.sub("", source)
    anchor = "    <section class=\"section split\">"
    if anchor not in source:
        raise ValueError("Subject root insertion point not found")
    source = source.replace(anchor, block + "\n\n" + anchor, 1)

    script_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL)
    if not script_match:
        raise ValueError("Subject root JSON-LD not found")
    data = json.loads(script_match.group(1))
    graph = data.get("@graph", [])
    published = [
        config for config in CONFIGS.values()
        if (ROOT / "과목별학원" / config["category"] / "index.html").exists()
    ]
    item_list = next((node for node in graph if node.get("@type") == "ItemList"), None)
    if item_list is None:
        raise ValueError("Subject root ItemList not found")
    item_list["name"] = "과목별·학년별 학습관리 안내"
    item_list["numberOfItems"] = len(published)
    item_list["itemListElement"] = [
        {
            "@type": "ListItem",
            "position": index,
            "name": config["display"],
            "url": absolute_url("과목별학원", config["category"]),
        }
        for index, config in enumerate(published, 1)
    ]
    webpage = next((node for node in graph if node.get("@type") in {"WebPage", "CollectionPage"}), None)
    if webpage is not None:
        webpage["url"] = absolute_url("과목별학원")
        webpage["dateModified"] = DATE_MODIFIED
        webpage["mainEntity"] = {"@id": item_list.get("@id", absolute_url("과목별학원") + "#itemlist")}
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    source = source[:script_match.start(1)] + encoded + source[script_match.end(1):]
    path.write_text(source, encoding="utf-8", newline="\n")


def update_sitemap(urls: list[str]) -> None:
    path = ROOT / "sitemap.xml"
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    existing: set[str] = set()
    last_modified: dict[str, str] = {}
    for node in root.findall("sm:url", ns):
        location = node.find("sm:loc", ns)
        modified = node.find("sm:lastmod", ns)
        if location is not None and location.text:
            existing.add(location.text)
            if modified is not None and modified.text:
                last_modified[location.text] = modified.text
    all_urls = list(existing)
    for url in urls:
        if url not in existing:
            all_urls.append(url)
            existing.add(url)
        last_modified[url] = DATE_MODIFIED
    home = DOMAIN + "/"
    ordered = [home] if home in existing else []
    ordered.extend(sorted(url for url in all_urls if url != home))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in ordered:
        modified = f"<lastmod>{last_modified[url]}</lastmod>" if url in last_modified else ""
        lines.append(f"  <url><loc>{escape(url)}</loc>{modified}</url>")
    lines.append("</urlset>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def update_llms() -> None:
    path = ROOT / "llms.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    published = [
        config for config in CONFIGS.values()
        if (ROOT / "과목별학원" / config["category"] / "index.html").exists()
    ]
    category_labels = {f"- {config['display']}:" for config in CONFIGS.values()}
    lines = [
        line for line in lines
        if not any(line.startswith(label) for label in category_labels)
    ]
    marker_index = next(
        (index for index, line in enumerate(lines) if line.startswith("- 과목별학원:")),
        None,
    )
    if marker_index is None:
        nationwide_index = next(
            (index for index, line in enumerate(lines) if line.startswith("- 전국학원:")),
            len(lines),
        )
        lines.insert(nationwide_index, f"- 과목별학원: {absolute_url('과목별학원')}")
        marker_index = nationwide_index
    category_lines = [
        f"- {config['display']}: {absolute_url('과목별학원', config['category'])}"
        for config in published
    ]
    lines[marker_index + 1:marker_index + 1] = category_lines
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def update_rss() -> None:
    path = ROOT / "rss.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel not found")
    published = [
        config for config in CONFIGS.values()
        if (ROOT / "과목별학원" / config["category"] / "index.html").exists()
    ]
    desired = [
        (
            "과목별학원 지역 안내",
            absolute_url("과목별학원"),
            "학년과 과목에 따라 구분한 지역별 학습관리 허브와 상담 기준을 안내합니다.",
        )
    ]
    desired.extend(
        (
            f"동네별 {config['display']}",
            absolute_url("과목별학원", config["category"]),
            config["card_description"],
        )
        for config in published
    )
    desired_urls = {url for _, url, _ in desired}
    for item in list(channel.findall("item")):
        link = item.findtext("link", "")
        if link in desired_urls:
            channel.remove(item)
    seoul = timezone(timedelta(hours=9))
    published_at = format_datetime(datetime.now(seoul).replace(hour=0, minute=0, second=0, microsecond=0))
    last_build = channel.find("lastBuildDate")
    if last_build is None:
        last_build = ET.Element("lastBuildDate")
        channel.insert(4, last_build)
    last_build.text = published_at
    insert_at = list(channel).index(last_build) + 1
    for title, url, description in desired:
        item = ET.Element("item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = url
        ET.SubElement(item, "description").text = description
        ET.SubElement(item, "pubDate").text = published_at
        channel.insert(insert_at, item)
        insert_at += 1
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    hub_only = os.environ.get("HUB_ONLY") == "1"
    manuscripts = read_zip_entries()
    rows = read_center_rows()
    slugs = make_slugs(rows)
    row_map = {normalize(row["근처 수업가능 동네"]): row for row in rows}
    manuscript_keys = {normalize(page["locality"]) for page in manuscripts}
    if manuscript_keys != set(row_map):
        raise ValueError(f"Manuscript/center mismatch: missing centers={sorted(manuscript_keys-set(row_map))[:10]}, missing manuscripts={sorted(set(row_map)-manuscript_keys)[:10]}")
    representatives = [] if hub_only else representative_urls()
    rendered: list[tuple[dict, dict]] = []
    TARGET.mkdir(parents=True, exist_ok=True)
    urls = [absolute_url("과목별학원"), absolute_url("과목별학원", CATEGORY)]
    for page in sorted(manuscripts, key=lambda item: item["locality"]):
        key = normalize(page["locality"])
        row = row_map[key]
        slug = slugs[key]
        center = center_payload(row, slug)
        page = sanitize_page(page, center)
        if not hub_only:
            parent = ROOT / "전국센터" / slug / "index.html"
            if not parent.exists():
                raise FileNotFoundError(f"Parent page missing: {parent}")
            representative = choose_representative(representatives, clean_text(page["sections"]["페이지타이틀"]))
            output = TARGET / slug / "index.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_page(page, center, representative), encoding="utf-8", newline="\n")
        rendered.append((page, center))
        urls.append(absolute_url("과목별학원", CATEGORY, slug))
    (TARGET / "index.html").write_text(render_hub(rendered), encoding="utf-8", newline="\n")
    if not hub_only:
        update_subject_root()
        update_sitemap(urls)
        update_llms()
        update_rss()
    print(json.dumps({"category": CATEGORY, "pages": len(rendered), "hub": str(TARGET / 'index.html'), "urls": len(urls)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
