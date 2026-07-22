from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import quote
import json
import re


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://xn--3e0bz50bxucwzc.com"
SITE_NAME = "전국수업.com"
SERVICE_NAME = "와와센터 학습코칭"
PHONE = "010-6839-8283"
PHONE_LINK = "01068398283"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"
SMS_URL = "https://blogsms.net/01068398283"
MODIFIED = "2026-07-22"
OG_IMAGE = f"{BASE}/assets/generated/site6-hero.webp"


GUIDES = [
    {
        "slug": "초등학생공부습관",
        "title": "초등학생 공부 습관 만드는 법",
        "description": "초등학생이 공부를 미루지 않도록 시작 신호, 적정 분량, 완료 기준과 학부모 점검 방법을 단계별로 정리했습니다.",
        "h1": "초등학생 공부 습관은 시작 행동부터 설계해야 합니다",
        "summary": "초등 공부 습관은 오래 앉아 있는 훈련이 아니라 정해진 시간에 시작하고, 할 일을 끝낸 뒤, 스스로 결과를 설명하는 흐름을 반복하면서 만들어집니다.",
        "audience": "초등학생과 학부모",
        "sections": [
            ("공부 시간보다 시작 신호를 먼저 고정합니다", ["매일 공부량을 크게 늘리기 전에 책상에 앉는 시간과 첫 과목을 일정하게 정합니다. 가방을 정리한 뒤 10분 휴식, 물 준비, 수학 연산처럼 순서를 고정하면 시작을 둘러싼 실랑이가 줄어듭니다.", "처음부터 한 시간을 요구하기보다 15~20분 안에 끝낼 수 있는 과제로 성공 경험을 만든 뒤 분량을 늘리는 편이 안정적입니다."], ["시작 시각과 첫 과목을 고정하기", "준비물은 시작 전에 한 번에 챙기기", "끝난 뒤 완료 표시를 직접 남기기"]),
            ("분량은 학생이 완료 여부를 판단할 수 있게 적습니다", ["‘수학 공부하기’보다 ‘연산 2쪽 풀고 틀린 문제 표시하기’처럼 완료 기준이 보여야 합니다. 과목·단원·분량·끝낸 뒤 할 일을 한 줄에 적으면 학생도 계획을 확인할 수 있습니다.", "계획을 지키지 못했을 때는 의지 부족으로 단정하지 않고 분량이 과했는지, 시작이 늦었는지, 문제 난도가 높았는지 나눠 봅니다."], ["과목과 단원을 함께 쓰기", "쪽수 또는 문제 수를 표시하기", "채점과 오답 확인까지 완료 기준에 넣기"]),
            ("읽기·계산·설명 활동을 함께 배치합니다", ["초등 시기에는 문제 수만 늘리는 것보다 지문을 소리 내어 읽고, 계산 과정을 적고, 오늘 배운 내용을 자기 말로 설명하는 활동이 중요합니다.", "설명하지 못하는 부분은 이해가 아직 불완전하다는 신호가 될 수 있으므로 다음 학습의 첫 과제로 남깁니다."], ["읽은 내용을 한 문장으로 요약하기", "계산 과정에서 바뀐 부호 확인하기", "어려웠던 문제를 말로 설명하기"]),
            ("학부모 점검은 결과 확인보다 질문 중심으로 합니다", ["정답 개수만 묻기보다 무엇이 어려웠는지, 계획보다 오래 걸린 이유가 무엇인지 질문합니다. 학생이 스스로 원인을 말하게 하면 다음 계획을 조정하기가 쉬워집니다.", "매일 긴 피드백을 하기보다 주 1회 기록을 함께 보며 잘된 행동 하나와 바꿀 행동 하나를 정하는 방식이 부담이 적습니다."], ["오늘 가장 오래 걸린 과목 묻기", "다시 풀어야 할 문제 확인하기", "다음 주에 바꿀 행동 하나만 정하기"]),
        ],
        "steps": ["정해진 시간에 같은 준비 순서로 시작", "작게 나눈 분량을 완료", "채점과 어려운 문제 표시", "주간 기록을 보며 다음 분량 조정"],
        "faq": [
            ("초등학생 공부 시간은 얼마나 길어야 하나요?", "학년만으로 시간을 정하기보다 현재 집중 가능한 길이에서 시작하는 것이 좋습니다. 짧게 완료하는 경험을 만든 뒤 과목 수와 분량을 조금씩 늘립니다."),
            ("계획표를 매일 쓰게 해야 하나요?", "매일 긴 계획표를 요구할 필요는 없습니다. 과목, 단원, 분량, 완료 여부처럼 실행 확인에 필요한 항목부터 간단히 기록합니다."),
            ("숙제를 자꾸 미루면 보상을 써도 되나요?", "일시적인 보상보다 시작 순서와 분량을 먼저 점검해야 합니다. 과제가 너무 크거나 시작 시점이 불규칙하면 보상만으로 습관이 유지되기 어렵습니다."),
            ("학부모가 채점까지 해줘야 하나요?", "처음에는 방법을 알려줄 수 있지만 점차 학생이 채점하고 틀린 문제를 표시하게 해야 합니다. 학부모는 기록이 남았는지 확인하는 역할이 적절합니다."),
        ],
        "related": ["학습플래너작성법", "수학오답관리", "학부모상담체크리스트"],
    },
    {
        "slug": "중학생내신공부법",
        "title": "중학생 내신 공부법과 시험 계획",
        "description": "중학생 내신 시험을 준비할 때 학교 진도, 교과서, 수행평가와 오답을 연결하는 주간 학습 계획을 안내합니다.",
        "h1": "중학생 내신 공부는 시험 범위와 실행 기록을 함께 봐야 합니다",
        "summary": "중등 내신은 문제집 한 권을 빨리 끝내는 것보다 학교 진도와 시험 범위를 기준으로 개념 확인, 유형 연습, 오답 재풀이의 시점을 나누는 것이 중요합니다.",
        "audience": "중학생과 학부모",
        "sections": [
            ("학교 일정과 시험 범위를 한 장에 모읍니다", ["과목별 시험 범위, 수행평가 일정, 제출 과제를 먼저 정리해야 실제 공부 가능한 시간이 보입니다. 일정이 흩어져 있으면 중요한 과제를 놓치거나 특정 과목에 시간이 쏠리기 쉽습니다.", "범위가 확정되기 전에는 학교 진도와 교과서 목차를 기준으로 예상 단원을 표시하고, 공지 후 바로 수정합니다."], ["시험일과 수행평가일 표시", "과목별 교과서 단원 정리", "제출 과제와 준비물 별도 표시"]),
            ("개념 확인과 문제풀이를 같은 날 몰아넣지 않습니다", ["개념을 읽은 직후에는 이해한 것처럼 느껴질 수 있습니다. 다음 날 핵심 내용을 빈 종이에 적거나 간단한 확인 문제를 풀어 기억이 남았는지 점검합니다.", "유형 문제는 맞힌 개수보다 막힌 이유를 남겨야 합니다. 개념 누락, 조건 해석, 계산, 암기 부족으로 원인을 나누면 복습 순서가 선명해집니다."], ["개념 학습 다음 날 회상 점검", "유형별로 대표 문제 선택", "틀린 이유를 짧게 기록"]),
            ("주간 계획에는 보충 시간을 미리 남깁니다", ["매일 계획을 꽉 채우면 수행평가나 추가 숙제가 생겼을 때 전체 일정이 무너집니다. 일주일 중 한두 구간은 밀린 과제와 오답을 처리하는 보충 시간으로 비워둡니다.", "주말에는 완료하지 못한 항목을 그대로 넘기기보다 분량 과다, 이해 부족, 시간 부족 중 원인을 고르고 다음 주 계획을 줄이거나 순서를 바꿉니다."], ["평일 과목별 핵심 과제 배치", "주 1~2회 보충 시간 확보", "일요일에 다음 주 분량 조정"]),
            ("시험 직전에는 새 문제보다 누적 오답을 봅니다", ["시험이 가까워질수록 새로운 교재를 늘리는 것보다 이미 틀렸던 문제와 헷갈렸던 개념을 다시 확인하는 편이 효율적입니다.", "실전 시간 안에 문제를 푼 뒤 남은 오답을 단원별로 묶으면 마지막 복습에서 무엇을 먼저 볼지 결정할 수 있습니다."], ["누적 오답을 단원별로 분류", "시간을 정해 실전처럼 풀기", "시험 전날 볼 핵심 항목 압축"]),
        ],
        "steps": ["학교 일정과 범위 통합", "개념 회상과 유형 연습", "주간 보충 시간 운영", "누적 오답 중심 최종 점검"],
        "faq": [
            ("중학교 시험공부는 몇 주 전부터 시작해야 하나요?", "과목 수와 현재 이해도에 따라 다르지만 시험 직전에 처음 범위를 보는 상황은 피해야 합니다. 범위가 나오기 전부터 학교 진도에 맞춰 개념과 기본 문제를 정리합니다."),
            ("교과서와 문제집 중 무엇을 먼저 봐야 하나요?", "학교 수업과 시험 범위를 확인하는 기준은 교과서와 수업 자료입니다. 개념을 확인한 뒤 문제집으로 유형을 연습하는 순서가 안정적입니다."),
            ("수행평가도 시험 계획에 포함해야 하나요?", "포함해야 합니다. 준비 시간이 겹치면 지필평가 공부 시간이 줄어들기 때문에 제출일과 준비 단계를 미리 계획에 넣습니다."),
            ("오답노트를 꼭 따로 만들어야 하나요?", "별도 노트가 목적은 아닙니다. 틀린 이유와 다시 풀 날짜를 확인할 수 있다면 문제집 표시나 간단한 기록표도 사용할 수 있습니다."),
        ],
        "related": ["시험4주학습계획", "학습플래너작성법", "수학오답관리"],
    },
    {
        "slug": "고등학생과목별공부법",
        "title": "고등학생 과목별 공부법",
        "description": "고등학생이 영어·수학·국어의 약점을 구분하고 내신 범위와 장기 학습을 함께 운영하는 과목별 공부 기준입니다.",
        "h1": "고등학생 공부는 과목별 약점과 시험 일정을 따로 설계해야 합니다",
        "summary": "고등 학습은 모든 과목에 같은 시간을 배분하기보다 영어·수학·국어의 현재 약점, 학교 시험 범위와 누적 학습 필요도를 나눠 우선순위를 정해야 합니다.",
        "audience": "고등학생과 학부모",
        "sections": [
            ("영어는 어휘·문법·독해의 병목을 구분합니다", ["독해가 느린 이유가 어휘 부족인지, 문장 구조 해석인지, 근거를 찾는 습관인지 먼저 구분합니다. 어휘가 부족한 상태에서 독해 문제만 늘리면 시간이 오래 걸리고 오답 원인이 남습니다.", "학교 시험에서는 교과서와 부교재 문장의 변형 가능성을 확인하고, 장기 학습에서는 처음 보는 지문을 읽는 연습을 별도로 유지합니다."], ["어휘 회상 테스트", "문장 구조와 수식 관계 표시", "선택지 근거를 지문에서 확인"]),
            ("수학은 단원별로 개념과 적용 수준을 분리합니다", ["공식을 알고 있는 것과 문제 조건에 적용하는 것은 다른 단계입니다. 대표 문제를 혼자 풀 수 있는지 확인한 뒤 유형 변화와 서술 과정으로 확장합니다.", "오답은 계산 실수와 개념 부족을 같은 방식으로 복습하지 않습니다. 실수는 검산 규칙을 만들고, 개념 부족은 관련 예제부터 다시 연결합니다."], ["개념을 말이나 식으로 설명", "대표 유형을 풀이 없이 재현", "오답 원인별 재시험 일정 설정"]),
            ("국어는 정답보다 근거를 찾는 과정을 남깁니다", ["문학과 독서 모두 선택지 판단 근거를 지문에서 찾는 연습이 필요합니다. 감으로 맞힌 문제도 근거를 설명하지 못하면 다시 확인할 대상으로 봅니다.", "학교 시험은 작품과 수업 자료를 세밀하게 정리하고, 장기적으로는 낯선 지문에서 문단 관계와 핵심 문장을 찾는 연습을 병행합니다."], ["문단별 핵심 역할 표시", "선택지의 맞고 틀린 근거 기록", "시간이 오래 걸린 지문 유형 분류"]),
            ("과목별 우선순위는 매주 다시 조정합니다", ["고정된 시간표만 지키기보다 학교 진도, 수행평가, 모의고사와 오답 결과에 따라 다음 주 비중을 바꿉니다.", "급한 과목만 반복하면 누적 학습이 필요한 과목이 밀릴 수 있으므로 유지 과제와 집중 과제를 나눠 배치합니다."], ["이번 주 집중 과목 1~2개 선정", "유지 과목의 최소 분량 확보", "주말에 결과를 보고 비중 재조정"]),
        ],
        "steps": ["과목별 병목 진단", "내신·장기 과제 분리", "집중·유지 과목 배치", "주간 결과로 시간 재배분"],
        "faq": [
            ("고등학생은 한 과목을 집중하는 것이 좋나요?", "취약 과목의 집중 시간이 필요하지만 다른 과목의 감각이 끊기지 않도록 최소 유지 분량을 함께 두는 것이 좋습니다."),
            ("내신과 모의고사 공부를 어떻게 나눠야 하나요?", "시험 기간에는 학교 범위 비중을 높이되, 평소에는 어휘·수학 누적 단원·국어 독해처럼 장기 과제를 유지합니다."),
            ("공부 시간이 긴데 성과가 적은 이유는 무엇인가요?", "복습 없이 문제만 이어가거나 막힌 이유를 기록하지 않으면 같은 실수가 반복될 수 있습니다. 완료한 양과 함께 이해·오답 결과를 확인해야 합니다."),
            ("과목별 계획은 얼마나 자주 바꿔야 하나요?", "일정을 매일 크게 바꾸기보다 주간 단위로 실행 결과와 학교 일정을 확인해 비중을 조정하는 방식이 안정적입니다."),
        ],
        "related": ["영어학습관리", "수학오답관리", "시험4주학습계획"],
    },
    {
        "slug": "영어학습관리",
        "title": "영어 어휘·문법·독해 학습관리",
        "description": "영어 성적을 구성하는 어휘, 문법, 문장 해석과 독해 근거 찾기를 진단하고 복습하는 구체적인 학습관리 방법입니다.",
        "h1": "영어 학습관리는 어휘·문법·독해의 연결 상태를 확인해야 합니다",
        "summary": "영어 문제를 많이 풀어도 같은 유형에서 막힌다면 어휘 회상, 문장 구조 해석, 지문 근거 확인 중 어느 단계가 끊기는지 먼저 확인해야 합니다.",
        "audience": "영어 학습이 필요한 초중고 학생",
        "sections": [
            ("어휘는 뜻을 읽는 것보다 떠올리는 연습이 필요합니다", ["단어장을 여러 번 읽는 것만으로는 지문에서 빠르게 의미가 떠오르지 않을 수 있습니다. 뜻을 가리고 말하거나 쓰는 회상 테스트를 짧게 반복합니다.", "틀린 단어는 무조건 처음부터 다시 외우기보다 혼동 단어, 철자 오류, 문맥 오해로 나눠 다음 테스트 분량에 넣습니다."], ["뜻 가리고 회상하기", "틀린 단어만 짧게 재시험", "문장 안에서 의미 확인하기"]),
            ("문법은 규칙 암기와 문장 적용을 연결합니다", ["문법 용어를 아는 것과 실제 문장에서 구조를 찾는 것은 다릅니다. 짧은 예문에서 주어·동사·수식 관계를 표시한 뒤 오류 수정과 문장 변형으로 확장합니다.", "자주 틀리는 문법은 정답만 적지 않고 왜 다른 선택지가 안 되는지 설명해야 구분 기준이 남습니다."], ["핵심 규칙 한 문장으로 설명", "예문에서 구조 표시", "오답 선택지의 오류 이유 기록"]),
            ("독해는 지문과 선택지의 근거를 연결합니다", ["읽은 뒤 느낌으로 답을 고르기보다 각 선택지의 판단 근거를 지문에서 표시합니다. 시간이 오래 걸린다면 어휘, 긴 문장, 문단 관계 중 어디에서 멈췄는지 기록합니다.", "문단별 핵심 역할을 짧게 남기면 전체 흐름을 놓치는 문제를 줄이고 다시 읽을 부분도 빠르게 찾을 수 있습니다."], ["문단 역할을 짧게 요약", "선택지 근거 문장 표시", "시간이 지연된 원인 기록"]),
            ("복습은 같은 문제 확인과 새 지문 적용을 나눕니다", ["틀린 문제의 해설을 이해한 뒤에는 풀이를 가리고 다시 설명합니다. 며칠 후 비슷한 유형의 새 문제에서도 같은 기준을 적용할 수 있는지 확인합니다.", "시험 전에는 누적 오답을 어휘·문법·독해로 나눠 취약 영역부터 다시 점검합니다."], ["해설 없이 다시 설명", "유사 유형으로 전이 확인", "시험 전 영역별 누적 복습"]),
        ],
        "steps": ["어휘 회상 점검", "문장 구조 적용", "지문 근거 확인", "유사 문제로 재확인"],
        "faq": [
            ("영어 단어는 하루에 몇 개가 적당한가요?", "정해진 개수보다 다음 날 회상할 수 있는 양이 중요합니다. 새 단어와 이전 오답 단어를 함께 테스트하며 유지 가능한 분량을 찾습니다."),
            ("문법을 공부해도 독해에 적용되지 않는 이유는 무엇인가요?", "규칙을 문제 선택지에서만 확인하고 실제 문장 구조를 분석하는 연습이 부족할 수 있습니다. 짧은 문장에서 구조를 표시하는 단계가 필요합니다."),
            ("독해 문제를 많이 풀면 속도가 빨라지나요?", "원인을 확인하지 않은 반복만으로는 제한적입니다. 어휘, 문장 구조, 문단 관계 중 시간이 걸리는 지점을 찾아 보완해야 합니다."),
            ("영어 오답은 어떻게 정리해야 하나요?", "단어 미암기, 문법 구분 실패, 근거 문장 오해, 시간 부족처럼 이유를 나누고 각 원인에 맞는 재학습 과제를 남깁니다."),
        ],
        "related": ["고등학생과목별공부법", "시험4주학습계획", "학습플래너작성법"],
    },
    {
        "slug": "수학오답관리",
        "title": "수학 오답 관리와 다시 풀기",
        "description": "수학 오답을 개념 부족, 조건 해석, 계산 실수와 시간 문제로 구분하고 일정 간격을 두고 다시 푸는 방법을 안내합니다.",
        "h1": "수학 오답 관리는 틀린 이유와 다시 풀 날짜를 남겨야 합니다",
        "summary": "수학 오답은 정답 풀이를 베껴 적는 것으로 끝내지 않고, 틀린 원인을 구분한 뒤 풀이를 가리고 재현하고, 며칠 뒤 다시 풀어야 실제 학습 기록이 됩니다.",
        "audience": "수학 오답이 반복되는 초중고 학생",
        "sections": [
            ("오답 원인을 네 가지로 먼저 나눕니다", ["개념을 몰랐는지, 조건을 놓쳤는지, 계산 과정에서 실수했는지, 시간 배분에 실패했는지 구분합니다. 원인이 다르면 다시 공부할 내용도 달라집니다.", "여러 원인이 겹쳤다면 가장 먼저 풀이를 멈추게 한 원인을 우선 표시하고 추가 원인을 함께 적습니다."], ["개념 부족", "조건·문장 해석", "계산·부호 실수", "풀이 순서·시간 부족"]),
            ("해설을 본 직후에는 풀이를 가리고 재현합니다", ["해설을 읽고 이해했다고 느끼는 것과 혼자 다시 푸는 것은 다릅니다. 해설을 덮은 뒤 첫 식을 왜 세웠는지 말하며 풀이를 다시 적습니다.", "재현하지 못하면 관련 개념 예제까지 돌아가고, 성공했다면 핵심 조건과 풀이 시작점을 짧게 남깁니다."], ["해설 없이 첫 단계 설명", "풀이 과정 전체 재현", "핵심 조건 한 줄 기록"]),
            ("시간 간격을 두고 같은 유형을 재시험합니다", ["당일에 바로 맞힌 문제는 기억의 영향이 큽니다. 이틀이나 일주일 뒤 다시 풀어 풀이 기준이 남았는지 확인합니다.", "같은 문제를 외워서 푸는 상황을 피하려면 숫자나 조건이 달라진 유사 문제를 함께 사용합니다."], ["당일 원인 정리", "2~3일 뒤 원문제 재풀이", "일주일 뒤 유사 문제 확인"]),
            ("시험 전에는 오답을 단원과 원인으로 압축합니다", ["모든 오답을 다시 보는 것보다 반복된 원인과 시험 범위에 해당하는 문제를 먼저 고릅니다. 단원별 대표 오답을 정하면 짧은 시간에도 복습 순서가 보입니다.", "계산 실수처럼 행동 규칙이 필요한 경우에는 검산 위치, 부호 확인, 조건 밑줄처럼 시험장에서 사용할 기준을 함께 정리합니다."], ["시험 범위 오답 우선", "반복 원인별 대표 문제 선정", "실전 확인 규칙 한 줄 작성"]),
        ],
        "steps": ["틀린 원인 분류", "해설 없이 풀이 재현", "간격을 둔 재시험", "시험 전 대표 오답 압축"],
        "faq": [
            ("수학 오답노트를 꼭 따로 써야 하나요?", "형식보다 다시 찾고 풀 수 있는지가 중요합니다. 문제집 표시, 사진, 간단한 기록표도 원인과 재풀이 날짜가 남는다면 사용할 수 있습니다."),
            ("계산 실수도 오답 정리를 해야 하나요?", "반복되는 계산 실수는 행동 규칙이 필요합니다. 실수가 발생한 위치와 검산 방법을 기록하고 비슷한 계산에서 다시 확인합니다."),
            ("오답은 몇 번 다시 풀어야 하나요?", "횟수를 고정하기보다 풀이를 설명할 수 있고 일정 시간이 지난 뒤에도 혼자 해결되는지 확인합니다. 다시 틀리면 개념 단계로 돌아갑니다."),
            ("해설을 오래 보는 것이 도움이 되나요?", "해설을 읽는 시간보다 덮은 뒤 스스로 재현하는 과정이 중요합니다. 이해되지 않는 단계만 표시해 개념이나 예제로 돌아갑니다."),
        ],
        "related": ["학습플래너작성법", "시험4주학습계획", "중학생내신공부법"],
    },
    {
        "slug": "시험4주학습계획",
        "title": "시험 4주 전 학습계획 세우기",
        "description": "시험 4주 전부터 범위 확인, 개념 복습, 유형 문제, 누적 오답과 실전 점검을 순서대로 배치하는 계획표입니다.",
        "h1": "시험 4주 학습계획은 범위·복습·오답 순서를 먼저 정해야 합니다",
        "summary": "시험 계획은 매일 공부 시간을 채우는 표가 아니라 남은 기간마다 해야 할 역할을 정하는 도구입니다. 4주 전에는 범위와 결손, 3주 전에는 개념, 2주 전에는 유형, 마지막 주에는 오답과 실전을 중심으로 봅니다.",
        "audience": "내신 시험을 준비하는 중고등학생",
        "sections": [
            ("4주 전: 일정과 범위를 모아 빈칸을 찾습니다", ["시험일, 수행평가, 제출 과제를 한 화면에 모으고 과목별 예상 범위를 표시합니다. 학교 진도에서 이해하지 못한 단원을 찾아 보충 순서를 정합니다.", "아직 범위가 확정되지 않았다면 교과서 목차와 수업 진도를 기준으로 계획하되 공지 후 바로 수정할 자리를 남깁니다."], ["시험·수행 일정 통합", "과목별 범위와 교재 확인", "취약 단원 우선순위 결정"]),
            ("3주 전: 개념을 회상하고 기본 문제로 확인합니다", ["노트를 읽는 데서 끝내지 않고 핵심 개념을 보지 않고 설명하거나 간단한 기본 문제를 풉니다. 막히는 부분은 관련 예제와 수업 자료로 돌아갑니다.", "암기 과목은 한 번에 몰아 외우지 않고 짧은 회상 테스트를 여러 날에 배치합니다."], ["개념을 보지 않고 설명", "기본·대표 문제 확인", "암기 항목 반복 간격 설정"]),
            ("2주 전: 유형 변화와 시간 배분을 연습합니다", ["기본 개념이 확인된 단원부터 조건이 달라진 문제와 서술형을 연습합니다. 맞힌 문제도 풀이 시간이 길거나 근거가 불분명했다면 점검 대상으로 남깁니다.", "과목별 예상 소요 시간을 기록해 마지막 주 실전 연습 순서를 정합니다."], ["유형별 대표 문제 풀이", "서술 과정과 근거 확인", "과목별 풀이 시간 기록"]),
            ("1주 전: 새 교재보다 누적 오답과 실전을 봅니다", ["누적 오답을 단원과 원인별로 압축하고 정해진 시간 안에 시험 범위를 풀어봅니다. 마지막 날까지 새로운 문제를 늘리면 이미 확인한 약점의 복습이 밀릴 수 있습니다.", "시험 전날에는 반복 실수, 암기 확인 항목, 자주 놓치는 조건을 한 장으로 줄여 확인합니다."], ["누적 오답 재풀이", "실전 시간으로 범위 점검", "마지막 확인표 한 장 만들기"]),
        ],
        "steps": ["4주 전 범위·결손 확인", "3주 전 개념·기본기", "2주 전 유형·서술·시간", "1주 전 오답·실전 압축"],
        "faq": [
            ("시험 범위가 늦게 나오면 계획을 어떻게 세우나요?", "학교 진도와 교과서 목차를 기준으로 예상 범위를 잡고 공지 후 조정합니다. 일정 전체를 비워두기보다 기본 개념을 미리 확인합니다."),
            ("계획을 지키지 못한 날은 다음 날 모두 해야 하나요?", "그대로 합치면 분량이 과해질 수 있습니다. 시험 중요도와 결손 정도를 보고 필수 과제와 줄일 과제를 나눕니다."),
            ("마지막 주에도 새 문제집을 풀어야 하나요?", "새 문제보다 이미 틀린 문제와 시험 범위 핵심을 우선합니다. 필요한 경우 확인용 문제만 선별해 사용합니다."),
            ("여러 과목 시험이 겹치면 어떻게 배분하나요?", "취약도, 시험 순서, 암기 유지 필요도를 함께 보고 집중 과목과 유지 과목을 나눕니다. 매주 결과에 따라 비중을 바꿉니다."),
        ],
        "related": ["중학생내신공부법", "고등학생과목별공부법", "학습플래너작성법"],
    },
    {
        "slug": "학습플래너작성법",
        "title": "학습 플래너 작성법과 점검 기준",
        "description": "과목·단원·분량·완료 기준을 적고 실제 공부 결과와 오답을 다음 계획에 연결하는 학습 플래너 작성법입니다.",
        "h1": "학습 플래너는 시간표보다 실행과 결과가 보여야 합니다",
        "summary": "실행되는 플래너는 ‘수학 2시간’처럼 시간만 적지 않습니다. 과목, 단원, 분량, 완료 기준을 적고 실제 소요 시간과 막힌 이유를 남겨 다음 계획을 조정합니다.",
        "audience": "계획은 세우지만 실행이 어려운 학생",
        "sections": [
            ("계획 한 줄에는 네 가지 정보가 필요합니다", ["과목·단원·분량·완료 기준을 함께 적으면 학생이 무엇을 끝내야 하는지 스스로 판단할 수 있습니다. ‘영어 공부’처럼 넓은 표현은 시작을 어렵게 만듭니다.", "큰 과제는 20~40분 안에 확인 가능한 단위로 나누고 채점이나 암기 테스트까지 완료 기준에 포함합니다."], ["과목과 단원", "쪽수·문제 수·단어 수", "채점·테스트 등 완료 기준"]),
            ("예상 시간과 실제 시간을 함께 남깁니다", ["예상과 실제 시간의 차이는 계획을 조정하는 근거가 됩니다. 오래 걸린 과제는 집중 문제인지, 난도 문제인지, 분량 문제인지 짧게 표시합니다.", "예상보다 빨리 끝났더라도 이해가 충분했는지 확인하고 남은 시간을 무조건 새 과제로 채우지 않습니다."], ["시작·종료 또는 실제 소요 시간", "지연된 이유 한 단어 기록", "이해도와 완료 상태 표시"]),
            ("완료하지 못한 과제는 원인을 보고 다시 배치합니다", ["미완료 항목을 다음 날 그대로 더하면 계획이 계속 밀릴 수 있습니다. 필수 여부를 판단하고 분량을 줄이거나 보충 시간으로 옮깁니다.", "반복해서 미뤄지는 과제는 학생의 의지보다 과제 크기, 시작 순서, 난도를 먼저 점검합니다."], ["필수·보충 과제 구분", "분량 축소 또는 순서 변경", "주간 보충 시간에 재배치"]),
            ("주간 점검에서 다음 계획의 기준을 만듭니다", ["일주일 기록을 보며 완료율만 평가하지 않고 오래 걸린 과목, 반복 오답, 시작이 어려웠던 시간대를 확인합니다.", "다음 주에는 잘된 행동 하나를 유지하고 바꿀 행동 하나만 구체적으로 정하면 계획이 과도하게 복잡해지는 것을 막을 수 있습니다."], ["과목별 실제 시간 비교", "반복된 미완료·오답 확인", "유지할 행동과 바꿀 행동 선정"]),
        ],
        "steps": ["구체적인 과제 작성", "실제 결과 기록", "미완료 원인 구분", "주간 점검 후 다음 계획 조정"],
        "faq": [
            ("플래너를 예쁘게 꾸미는 것이 도움이 되나요?", "작성 동기를 높일 수 있지만 기록 자체가 목적이 되면 시간이 많이 듭니다. 실행과 결과를 확인하는 항목을 우선합니다."),
            ("매일 계획을 모두 지켜야 하나요?", "완벽한 완료보다 지키지 못한 이유를 확인해 다음 분량을 조정하는 것이 중요합니다. 보충 시간을 미리 두면 일정이 덜 무너집니다."),
            ("공부 시간만 기록해도 되나요?", "시간만으로는 어떤 단원을 얼마나 끝냈는지 알기 어렵습니다. 분량과 완료 기준, 어려웠던 부분을 함께 남깁니다."),
            ("학부모는 플래너를 어떻게 확인해야 하나요?", "매일 지적하기보다 주간 기록을 함께 보며 반복된 어려움과 다음 계획을 질문하는 방식이 좋습니다."),
        ],
        "related": ["초등학생공부습관", "시험4주학습계획", "학부모상담체크리스트"],
    },
    {
        "slug": "학부모상담체크리스트",
        "title": "학부모 학습상담 체크리스트",
        "description": "학습상담 전에 준비할 시험지, 공부 시간, 오답과 숙제 기록 및 상담에서 확인해야 할 관리 기준을 정리했습니다.",
        "h1": "학부모 학습상담은 자료와 질문을 준비하면 더 구체적입니다",
        "summary": "상담에서는 성적만 전달하기보다 최근 시험지, 반복 오답, 실제 공부 시간과 숙제 수행 기록을 함께 봐야 학생에게 필요한 보충 순서와 관리 방식을 구체적으로 정할 수 있습니다.",
        "audience": "학습상담을 준비하는 학부모",
        "sections": [
            ("최근 결과보다 반복되는 패턴을 준비합니다", ["시험 점수 한 번보다 어떤 단원에서 자주 틀리는지, 숙제를 언제 미루는지, 시험공부를 언제 시작하는지가 상담 방향을 정하는 데 도움이 됩니다.", "자료가 모두 없어도 최근 어려웠던 문제와 생활 패턴을 메모하면 상담에서 확인할 질문을 만들 수 있습니다."], ["최근 시험지 또는 오답 문제", "평일·주말 실제 공부 시간", "숙제와 복습 수행 여부"]),
            ("과목별로 막히는 순간을 구체적으로 말합니다", ["‘수학을 어려워한다’보다 문제 조건을 읽고 식을 못 세우는지, 계산은 되지만 응용이 어려운지 설명하면 진단 범위를 좁힐 수 있습니다.", "영어도 단어 암기, 문장 해석, 긴 지문, 서술형 중 어느 단계에서 시간이 걸리는지 나눠 전달합니다."], ["혼자 시작할 수 있는 과제", "도움이 필요한 단원과 유형", "자주 포기하거나 시간이 길어지는 지점"]),
            ("수업보다 관리 흐름을 질문합니다", ["교재와 수업 시간뿐 아니라 진단 결과가 계획에 어떻게 반영되는지, 숙제와 오답을 언제 다시 확인하는지 물어봅니다.", "학부모에게 전달되는 피드백의 주기와 학생이 계획을 지키지 못했을 때 조정하는 방식도 확인할 항목입니다."], ["진단 후 우선순위 설정 방식", "플래너·숙제·오답 확인 주기", "학부모 피드백 내용과 시점"]),
            ("상담 당일에 모든 것을 결정할 필요는 없습니다", ["학생에게 필요한 보충 순서와 기대하는 관리 방식을 먼저 정리한 뒤 실제 일정, 이동, 비용과 함께 판단합니다.", "상담 후에는 학생과 공유할 내용과 학부모만 점검할 내용을 나눠 불필요한 압박을 줄이는 것이 좋습니다."], ["학생에게 필요한 첫 과제 정리", "등원 일정과 실제 실행 가능성 확인", "상담 후 한 주 동안 관찰할 행동 선정"]),
        ],
        "steps": ["시험지·오답·생활 기록 준비", "과목별 막히는 지점 설명", "관리와 피드백 방식 질문", "상담 후 첫 실행 기준 정리"],
        "faq": [
            ("시험지가 없어도 학습상담을 받을 수 있나요?", "가능합니다. 최근 어려웠던 단원, 숙제 수행, 공부 시간과 반복되는 행동을 알려주면 상담에서 필요한 진단 항목을 정할 수 있습니다."),
            ("학생도 상담에 함께 참여해야 하나요?", "학생이 느끼는 어려움과 학부모가 보는 모습이 다를 수 있어 가능한 경우 함께 확인하는 것이 좋습니다. 상황에 따라 학부모 사전 상담도 가능합니다."),
            ("상담에서 수업 교재만 확인하면 되나요?", "교재 외에도 진단, 계획, 숙제, 오답 재학습, 피드백이 어떤 흐름으로 이어지는지 확인해야 합니다."),
            ("상담 후 무엇을 먼저 관찰해야 하나요?", "첫 주에는 공부 시작 시간, 계획 완료 여부, 반복 오답처럼 한두 가지 행동을 정해 관찰하는 것이 좋습니다."),
        ],
        "related": ["초등학생공부습관", "중학생내신공부법", "학습플래너작성법"],
    },
]


def canonical(path: str = "") -> str:
    if not path:
        return f"{BASE}/"
    return f"{BASE}/{quote(path.strip('/'), safe='/')}/"


def organization() -> dict:
    return {
        "@type": "EducationalOrganization",
        "@id": f"{BASE}/#organization",
        "name": SERVICE_NAME,
        "alternateName": SITE_NAME,
        "url": f"{BASE}/",
        "logo": f"{BASE}/assets/favicon.png",
        "telephone": PHONE,
        "openingHours": "Mo-Sa 12:00-24:00",
        "areaServed": {"@type": "Country", "name": "대한민국"},
        "knowsAbout": ["학습 진단", "플래너 관리", "오답 재학습", "초등 학습 습관", "중등 내신 관리", "고등 과목별 학습관리"],
        "contactPoint": {"@type": "ContactPoint", "telephone": "+82-10-6839-8283", "contactType": "학습 상담", "availableLanguage": "Korean"},
    }


def json_script(graph: list[dict]) -> str:
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{payload}</script>'


def guide_graph(guide: dict) -> list[dict]:
    page_url = canonical(f"학습가이드/{guide['slug']}")
    hub_url = canonical("학습가이드")
    faq = [
        {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
        for question, answer in guide["faq"]
    ]
    return [
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": f"{guide['title']} | {SITE_NAME}",
            "description": guide["description"],
            "inLanguage": "ko-KR",
            "isPartOf": {"@id": f"{BASE}/#website"},
            "publisher": {"@id": f"{BASE}/#organization"},
            "breadcrumb": {"@id": f"{page_url}#breadcrumb"},
            "mainEntity": {"@id": f"{page_url}#article"},
            "dateModified": MODIFIED,
        },
        {
            "@type": "Article",
            "@id": f"{page_url}#article",
            "headline": guide["h1"],
            "description": guide["description"],
            "datePublished": MODIFIED,
            "dateModified": MODIFIED,
            "inLanguage": "ko-KR",
            "author": {"@id": f"{BASE}/#organization"},
            "publisher": {"@id": f"{BASE}/#organization"},
            "sourceOrganization": {"@id": f"{BASE}/#organization"},
            "mainEntityOfPage": {"@id": f"{page_url}#webpage"},
            "isBasedOn": {"@id": f"{hub_url}#webpage"},
            "articleSection": [heading for heading, _, _ in guide["sections"]],
            "about": [{"@type": "Thing", "name": guide["title"]}, {"@type": "Thing", "name": guide["audience"]}],
            "hasPart": [{"@id": f"{page_url}#steps"}, {"@id": f"{page_url}#faq"}],
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{page_url}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "홈", "item": f"{BASE}/"},
                {"@type": "ListItem", "position": 2, "name": "학습가이드", "item": hub_url},
                {"@type": "ListItem", "position": 3, "name": guide["title"], "item": page_url},
            ],
        },
        organization(),
        {
            "@type": "ItemList",
            "@id": f"{page_url}#steps",
            "name": f"{guide['title']} 실행 순서",
            "itemListElement": [
                {"@type": "ListItem", "position": index, "name": item}
                for index, item in enumerate(guide["steps"], start=1)
            ],
        },
        {"@type": "FAQPage", "@id": f"{page_url}#faq", "mainEntity": faq},
    ]


def brand(prefix: str) -> str:
    return (
        f'<a class="brand" href="{prefix}" aria-label="{SITE_NAME} 홈">'
        '<span class="brand-mark">W</span>'
        f'<span class="brand-copy"><strong>{SITE_NAME}</strong><small>{SERVICE_NAME}</small></span>'
        '</a>'
    )


def floating() -> str:
    return f'''<aside class="floating-actions" aria-label="빠른 상담 버튼">
    <a href="tel:{PHONE}">전화문의</a>
    <a href="{SMS_URL}" target="_blank" rel="noopener">문자문의</a>
    <a href="{FORM_URL}" target="_blank" rel="noopener">상담신청</a>
  </aside>'''


def guide_card(guide: dict, prefix: str = "") -> str:
    return (
        f'<a class="guide-library-card" href="{prefix}{guide["slug"]}/">'
        f'<span>{escape(guide["audience"])}</span><h3>{escape(guide["title"])}</h3>'
        f'<p>{escape(guide["description"])}</p><b>가이드 읽기 <span aria-hidden="true">→</span></b></a>'
    )


def guide_page(guide: dict) -> str:
    page_url = canonical(f"학습가이드/{guide['slug']}")
    sections = []
    for heading, paragraphs, bullets in guide["sections"]:
        paragraph_html = "".join(f"<p>{escape(text)}</p>" for text in paragraphs)
        bullet_html = "".join(f"<li>{escape(item)}</li>" for item in bullets)
        sections.append(f'<section class="info-section"><h2>{escape(heading)}</h2>{paragraph_html}<ul class="info-checks">{bullet_html}</ul></section>')
    steps = "".join(f'<li><span>{index:02d}</span><p>{escape(item)}</p></li>' for index, item in enumerate(guide["steps"], start=1))
    faqs = "".join(f'<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q, a in guide["faq"])
    guide_by_slug = {item["slug"]: item for item in GUIDES}
    related = "".join(guide_card(guide_by_slug[slug], "../") for slug in guide["related"])
    toc = "".join(f'<a href="#section-{index}">{escape(heading)}</a>' for index, (heading, _, _) in enumerate(guide["sections"], start=1))
    for index in range(1, len(sections) + 1):
        sections[index - 1] = sections[index - 1].replace('class="info-section"', f'class="info-section" id="section-{index}"', 1)
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(guide['title'])} | {SITE_NAME}</title>
  <meta name="description" content="{escape(guide['description'])}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ko_KR">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{escape(guide['title'])} | {SITE_NAME}">
  <meta property="og:description" content="{escape(guide['description'])}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:image" content="{OG_IMAGE}">
  <meta property="article:published_time" content="{MODIFIED}">
  <meta property="article:modified_time" content="{MODIFIED}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(guide['title'])} | {SITE_NAME}">
  <meta name="twitter:description" content="{escape(guide['description'])}">
  <meta name="twitter:image" content="{OG_IMAGE}">
  <link rel="canonical" href="{page_url}">
  <link rel="alternate" type="application/rss+xml" title="{SITE_NAME} 학습정보 RSS" href="{BASE}/rss.xml">
  <link rel="icon" href="../../assets/favicon.png">
  <link rel="stylesheet" href="../../assets/site.css">
  <link rel="stylesheet" href="../../assets/site-modern.css">
  {json_script(guide_graph(guide))}
</head>
<body class="general-page info-guide-page">
  <header class="site-header"><div class="header-inner">
    {brand('../../')}
    <nav class="nav" aria-label="상단 메뉴"><a href="../../">홈</a><a href="../" aria-current="page">학습가이드</a><a href="../../상담문의/">상담문의</a><a href="../../과목별학원/">과목별학원</a><a href="../../전국센터/">전국학원</a></nav>
    <a class="header-cta" href="{FORM_URL}" target="_blank" rel="noopener">상담 신청</a>
  </div></header>
  <main>
    <nav class="guide-breadcrumb" aria-label="현재 위치"><a href="../../">홈</a><span>›</span><a href="../">학습가이드</a><span>›</span><strong>{escape(guide['title'])}</strong></nav>
    <section class="page-hero info-hero"><p class="eyebrow">Practical Study Guide</p><h1>{escape(guide['h1'])}</h1><p class="lead">{escape(guide['description'])}</p></section>
    <section class="section info-summary"><p class="eyebrow">핵심 답변</p><h2>먼저 확인할 기준</h2><p>{escape(guide['summary'])}</p><div class="info-audience"><span>대상</span><b>{escape(guide['audience'])}</b></div></section>
    <nav class="info-toc" aria-label="이 페이지의 목차"><strong>이 페이지에서 확인할 내용</strong><div>{toc}</div></nav>
    <article class="section info-article">{''.join(sections)}</article>
    <section class="section info-step-section"><div class="section-head"><p class="eyebrow">Action Flow</p><h2>실행 순서로 다시 정리하기</h2></div><ol class="info-steps">{steps}</ol></section>
    <section class="section"><div class="section-head center"><p class="eyebrow">FAQ</p><h2>{escape(guide['title'])} 자주 묻는 질문</h2></div><div class="faq" id="faq">{faqs}</div></section>
    <section class="section evidence-wrap"><div class="evidence-note"><div><p class="eyebrow">작성·검토 기준</p><h2>실제 학습 기록을 확인하는 기준으로 정리했습니다</h2></div><dl><div><dt>작성 주체</dt><dd>{SERVICE_NAME}</dd></div><div><dt>정보 기준</dt><dd>학습 진단·플래너·오답 재학습 상담 항목</dd></div><div><dt>최근 검토</dt><dd>2026년 7월 22일</dd></div></dl></div></section>
    <section class="section"><div class="section-head"><p class="eyebrow">Related Guides</p><h2>함께 보면 좋은 학습가이드</h2></div><div class="related-guide-grid">{related}</div></section>
    <section class="section"><div class="cta-box"><p class="eyebrow">Consulting</p><h2>학생의 현재 기록을 기준으로 상담을 시작해보세요</h2><p class="lead">최근 시험지, 어려운 단원과 실제 공부 시간을 준비하면 필요한 관리 순서를 더 구체적으로 확인할 수 있습니다.</p><div class="actions" style="justify-content:center"><a class="btn btn-primary" href="../../상담문의/">상담 준비 확인</a><a class="btn btn-soft" href="tel:{PHONE_LINK}">전화 문의</a></div></div></section>
  </main>
  <footer class="footer"><div class="footer-inner"><div><strong>{SITE_NAME}</strong><br>{SERVICE_NAME} · 초중고 학습관리 정보</div><div>상담 전화 <a href="tel:{PHONE_LINK}">{PHONE}</a></div></div></footer>
  {floating()}
</body>
</html>
'''


def extract_graph(html: str) -> dict:
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if not match:
        raise ValueError("JSON-LD script not found")
    return json.loads(match.group(1))


def absolutize(value, page_url: str):
    if isinstance(value, dict):
        return {key: absolutize(item, page_url) for key, item in value.items()}
    if isinstance(value, list):
        return [absolutize(item, page_url) for item in value]
    if not isinstance(value, str):
        return value
    if value == "/":
        return f"{BASE}/"
    if value.startswith("/#") or value.startswith("/assets/"):
        return f"{BASE}{value}"
    if value == "./":
        return page_url
    if value.startswith("./#"):
        return f"{page_url}{value[2:]}"
    if value == "../":
        return f"{BASE}/"
    return value


def replace_jsonld(html: str, graph: dict) -> str:
    return re.sub(r'<script type="application/ld\+json">.*?</script>', json_script(graph["@graph"]), html, count=1, flags=re.S)


def set_meta(html: str, attr: str, key: str, content: str) -> str:
    pattern = rf'<meta\s+{attr}="{re.escape(key)}"\s+content="[^"]*"\s*/?>'
    replacement = f'<meta {attr}="{key}" content="{escape(content, quote=True)}">'
    if re.search(pattern, html):
        return re.sub(pattern, replacement, html, count=1)
    return html.replace("</title>", f"</title>\n  {replacement}", 1)


def enrich_social(html: str, title: str, description: str, page_url: str, article: bool = False) -> str:
    html = re.sub(r'<title>.*?</title>', f'<title>{escape(title)}</title>', html, count=1, flags=re.S)
    html = set_meta(html, "name", "description", description)
    html = set_meta(html, "name", "robots", "index,follow,max-image-preview:large")
    html = set_meta(html, "property", "og:type", "article" if article else "website")
    html = set_meta(html, "property", "og:title", title)
    html = set_meta(html, "property", "og:description", description)
    html = set_meta(html, "property", "og:url", page_url)
    for key, value in [
        ("og:locale", "ko_KR"), ("og:site_name", SITE_NAME), ("og:image", OG_IMAGE),
    ]:
        html = set_meta(html, "property", key, value)
    for key, value in [
        ("twitter:card", "summary_large_image"), ("twitter:title", title),
        ("twitter:description", description), ("twitter:image", OG_IMAGE),
    ]:
        html = set_meta(html, "name", key, value)
    html = re.sub(r'<link rel="canonical" href="[^"]+">', f'<link rel="canonical" href="{page_url}">', html, count=1)
    if 'type="application/rss+xml"' not in html:
        html = html.replace('<link rel="icon"', f'<link rel="alternate" type="application/rss+xml" title="{SITE_NAME} 학습정보 RSS" href="{BASE}/rss.xml">\n  <link rel="icon"', 1)
    return html


def update_graph(html: str, page_url: str, kind: str) -> str:
    payload = extract_graph(html)
    payload = absolutize(payload, page_url)
    graph = payload["@graph"]
    page_labels = {
        "home": (
            f"초중고 영어·수학·국어 학습코칭 | {SITE_NAME}",
            "전국수업.com은 초등·중등·고등 학생의 영어·수학·국어 학습 진단부터 플래너, 오답 재학습과 시험 대비까지 연결하는 학습코칭 정보를 제공합니다.",
        ),
        "guide": (
            f"초중고 학습가이드 | 진단·플래너·오답 재학습 | {SITE_NAME}",
            "초등 공부 습관, 중등 내신, 고등 과목별 공부법부터 플래너 작성과 오답 재학습, 시험 4주 계획까지 구체적으로 정리한 학습가이드입니다.",
        ),
        "contact": (
            f"초중고 학습 상담문의와 진단 준비 | {SITE_NAME}",
            "초중고 학습 상담 전 준비할 시험지, 오답, 공부 시간과 숙제 기록 및 상담에서 확인할 진단·플래너·피드백 항목을 안내합니다.",
        ),
    }
    page_name, page_description = page_labels[kind]
    for node in graph:
        node_type = node.get("@type")
        if node_type == "WebSite":
            node.update({"@id": f"{BASE}/#website", "url": f"{BASE}/", "name": SITE_NAME, "alternateName": SERVICE_NAME})
        if node_type in {"WebPage", "ContactPage"}:
            node["url"] = page_url
            node["name"] = page_name
            node["description"] = page_description
            node["dateModified"] = MODIFIED
        if node_type == "EducationalOrganization":
            node["alternateName"] = SITE_NAME
        if node_type == "Article":
            node["dateModified"] = MODIFIED
            node["sourceOrganization"] = {"@id": f"{BASE}/#organization"}
            node["isBasedOn"] = {"@id": f"{canonical('학습가이드')}#webpage"} if kind != "guide" else {"@id": f"{BASE}/#webpage"}
    if kind == "guide":
        graph[:] = [node for node in graph if node.get("@id") != f"{page_url}#guide-library"]
        library = {
            "@type": "ItemList",
            "@id": f"{page_url}#guide-library",
            "name": "학생과 학부모를 위한 학습가이드",
            "numberOfItems": len(GUIDES),
            "itemListElement": [
                {"@type": "ListItem", "position": index, "name": guide["title"], "url": canonical(f"학습가이드/{guide['slug']}")}
                for index, guide in enumerate(GUIDES, start=1)
            ],
        }
        graph.append(library)
        for node in graph:
            if node.get("@type") == "WebPage":
                node["hasPart"] = [
                    item for item in node.get("hasPart", [])
                    if item.get("@id") != f"{page_url}#guide-library"
                ] + [{"@id": f"{page_url}#guide-library"}]
    return replace_jsonld(html, payload)


def replace_brand_and_footer(html: str, prefix: str) -> str:
    html = re.sub(r'<a class="brand"[^>]*>.*?</a>', brand(prefix), html, count=1, flags=re.S)
    html = html.replace('<body>', '<body class="general-page">', 1)
    html = html.replace('<strong>와와센터 학습코칭</strong><br>', f'<strong>{SITE_NAME}</strong><br>{SERVICE_NAME} · ')
    return html


def evidence_block() -> str:
    return f'''    <section class="section evidence-wrap">
      <div class="evidence-note"><div><p class="eyebrow">작성·검토 기준</p><h2>학습 진단과 실행 기록을 기준으로 안내합니다</h2></div><dl><div><dt>작성 주체</dt><dd>{SERVICE_NAME}</dd></div><div><dt>정보 기준</dt><dd>상담·플래너·오답 재학습 관리 항목</dd></div><div><dt>최근 검토</dt><dd>2026년 7월 22일</dd></div></dl></div>
    </section>

'''


def update_existing_pages() -> None:
    home_path = ROOT / "index.html"
    home = home_path.read_text(encoding="utf-8")
    home_title = f"초중고 영어·수학·국어 학습코칭 | {SITE_NAME}"
    home_desc = "전국수업.com은 초등·중등·고등 학생의 영어·수학·국어 학습 진단부터 플래너, 오답 재학습과 시험 대비까지 연결하는 학습코칭 정보를 제공합니다."
    home = enrich_social(home, home_title, home_desc, canonical())
    home = update_graph(home, canonical(), "home")
    home = replace_brand_and_footer(home, "./")
    home = home.replace('<p class="eyebrow">Learning Coaching</p>\n        <h1>공부를 시키는 곳보다<br>공부가 굴러가게 만드는 곳</h1>', '<p class="eyebrow">전국수업.com · Learning Coaching</p>\n        <h1>초중고 영어·수학·국어 학습코칭,<br>공부가 실행되는 흐름을 만듭니다</h1>')
    home = re.sub(
        r'(?:전국수업\.com의 )*와와센터 학습코칭은 학생의 현재 실력과 공부 습관을 먼저 살피고,',
        '전국수업.com의 와와센터 학습코칭은 학생의 현재 실력과 공부 습관을 먼저 살피고,',
        home,
        count=1,
    )
    home = home.replace('<img src="assets/generated/site6-hero.png" alt="와와센터 학습코칭 상담 장면">', '<img src="assets/generated/site6-hero.png" alt="와와센터 초중고 학습코칭 상담 장면" width="1702" height="924" fetchpriority="high" decoding="async">')
    home = home.replace('href="학습가이드/">\n          <h3>학습 진단</h3>', 'href="학습가이드/학부모상담체크리스트/">\n          <h3>학습 진단</h3>', 1)
    home = home.replace('href="학습가이드/">\n          <h3>플래너 관리</h3>', 'href="학습가이드/학습플래너작성법/">\n          <h3>플래너 관리</h3>', 1)
    home = home.replace('href="학습가이드/">\n          <h3>오답 재학습</h3>', 'href="학습가이드/수학오답관리/">\n          <h3>오답 재학습</h3>', 1)
    home = home.replace('기존 와와학습코칭센터 메인 안내 기준을 참고해, 보호자님이 가장 궁금해하는 비용 정보를 보기 쉽게 정리했습니다.', '현재 사이트에 제공된 지역별 교습비 안내를 기준으로 초등·중등·고등 수업료를 정리했습니다. 실제 적용 금액은 상담에서 센터별 등록 정보를 다시 확인합니다.')
    marker = '    <section class="section">\n      <div class="cta-box">'
    if '작성·검토 기준' not in home:
        home = home.replace(marker, evidence_block() + marker, 1)
    home_path.write_text(home, encoding="utf-8", newline="\n")

    guide_path = ROOT / "학습가이드" / "index.html"
    guide_html = guide_path.read_text(encoding="utf-8")
    guide_title = f"초중고 학습가이드 | 진단·플래너·오답 재학습 | {SITE_NAME}"
    guide_desc = "초등 공부 습관, 중등 내신, 고등 과목별 공부법부터 플래너 작성과 오답 재학습, 시험 4주 계획까지 구체적으로 정리한 학습가이드입니다."
    guide_url = canonical("학습가이드")
    guide_html = enrich_social(guide_html, guide_title, guide_desc, guide_url, article=True)
    guide_html = update_graph(guide_html, guide_url, "guide")
    guide_html = replace_brand_and_footer(guide_html, "../")
    guide_html = guide_html.replace('<h1>공부법은 추상적이면<br>실행되지 않습니다.</h1>', '<h1>학습 진단·플래너·오답 재학습<br>실행 중심 학습가이드</h1>')
    guide_html = guide_html.replace('와와센터 학습코칭은 학생이 실제로 움직일 수 있도록', '공부법은 추상적이면 실행되지 않습니다. 전국수업.com은 학생이 실제로 움직일 수 있도록', 1)
    library_cards = "".join(guide_card(item) for item in GUIDES)
    library = f'''    <section class="section guide-library-section">
      <div class="section-head"><p class="eyebrow">Guide Library</p><h2>학생 상황에 맞는 학습가이드를 선택하세요</h2><p class="lead">학년과 과목, 시험 일정과 상담 목적에 따라 바로 확인할 수 있도록 주제를 나눴습니다.</p></div>
      <div class="guide-library-grid">{library_cards}</div>
    </section>

'''
    first_section = '    <section class="section split">'
    if 'guide-library-section' not in guide_html:
        guide_html = guide_html.replace(first_section, library + first_section, 1)
    cta_marker = '    <section class="section">\n      <div class="cta-box">'
    if '작성·검토 기준' not in guide_html:
        guide_html = guide_html.replace(cta_marker, evidence_block() + cta_marker, 1)
    guide_path.write_text(guide_html, encoding="utf-8", newline="\n")

    contact_path = ROOT / "상담문의" / "index.html"
    contact = contact_path.read_text(encoding="utf-8")
    contact_title = f"초중고 학습 상담문의와 진단 준비 | {SITE_NAME}"
    contact_desc = "초중고 학습 상담 전 준비할 시험지, 오답, 공부 시간과 숙제 기록 및 상담에서 확인할 진단·플래너·피드백 항목을 안내합니다."
    contact_url = canonical("상담문의")
    contact = enrich_social(contact, contact_title, contact_desc, contact_url)
    contact = update_graph(contact, contact_url, "contact")
    contact = replace_brand_and_footer(contact, "../")
    contact = contact.replace('<h1>상담은 불안을 말하는 시간이 아니라<br>관리 기준을 정하는 시간입니다.</h1>', '<h1>초중고 학습 상담문의와<br>진단 준비 안내</h1>')
    contact = re.sub(
        r'(?:상담은 불안을 말하는 시간이 아니라 관리 기준을 정하는 과정입니다\. )*최근 시험지, 공부 시간, 숙제 습관,',
        '상담은 불안을 말하는 시간이 아니라 관리 기준을 정하는 과정입니다. 최근 시험지, 공부 시간, 숙제 습관,',
        contact,
        count=1,
    )
    cta_marker = '    <section class="section">\n      <div class="cta-box">'
    if '작성·검토 기준' not in contact:
        contact = contact.replace(cta_marker, evidence_block() + cta_marker, 1)
    contact_path.write_text(contact, encoding="utf-8", newline="\n")


def write_guides() -> None:
    base = ROOT / "학습가이드"
    for guide in GUIDES:
        target = base / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(guide_page(guide), encoding="utf-8", newline="\n")


def update_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    urls = [canonical(), canonical("학습가이드"), canonical("상담문의")]
    urls.extend(canonical(f"학습가이드/{guide['slug']}") for guide in GUIDES)
    for url in urls:
        pattern = rf'\s*<url><loc>{re.escape(url)}</loc>(?:<lastmod>[^<]+</lastmod>)?</url>'
        entry = f'\n  <url><loc>{url}</loc><lastmod>{MODIFIED}</lastmod></url>'
        if re.search(pattern, text):
            text = re.sub(pattern, entry, text, count=1)
        else:
            text = text.replace("\n</urlset>", f"{entry}\n</urlset>")
    path.write_text(text, encoding="utf-8", newline="\n")


def write_rss() -> None:
    items = [
        ("초중고 학습가이드", "학습가이드", "학생과 학부모가 학년·과목·상황별로 확인할 수 있는 실행 중심 학습가이드입니다."),
        *[(guide["title"], f"학습가이드/{guide['slug']}", guide["description"]) for guide in GUIDES],
    ]
    item_xml = "".join(
        f'''    <item><title>{escape(title)}</title><link>{canonical(path)}</link><guid isPermaLink="true">{canonical(path)}</guid><description>{escape(description)}</description><pubDate>Wed, 22 Jul 2026 00:00:00 +0900</pubDate></item>\n'''
        for title, path, description in items
    )
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>{SITE_NAME} 학습정보</title><link>{BASE}/</link><description>{SERVICE_NAME}의 초중고 학습관리 가이드</description><language>ko</language><lastBuildDate>Wed, 22 Jul 2026 00:00:00 +0900</lastBuildDate>
{item_xml}</channel></rss>
'''
    (ROOT / "rss.xml").write_text(rss, encoding="utf-8", newline="\n")


def update_llms() -> None:
    path = ROOT / "llms.txt"
    text = path.read_text(encoding="utf-8")
    marker = "- 상담문의: https://xn--3e0bz50bxucwzc.com/상담문의/"
    guide_lines = "\n".join(
        f"- {guide['title']}: {canonical('학습가이드/' + guide['slug'])}"
        for guide in GUIDES
    )
    if guide_lines not in text:
        text = text.replace(marker, f"{marker}\n{guide_lines}")
    if "- 학습정보 RSS:" not in text:
        text = text.replace("- 사이트맵: https://xn--3e0bz50bxucwzc.com/sitemap.xml", "- 사이트맵: https://xn--3e0bz50bxucwzc.com/sitemap.xml\n- 학습정보 RSS: https://xn--3e0bz50bxucwzc.com/rss.xml")
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    update_existing_pages()
    write_guides()
    update_sitemap()
    write_rss()
    update_llms()
    print(json.dumps({"updated": 3, "created_guides": len(GUIDES), "modified": MODIFIED}, ensure_ascii=False))


if __name__ == "__main__":
    main()
