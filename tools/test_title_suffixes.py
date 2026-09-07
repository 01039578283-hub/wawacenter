import unittest
from personalize_title_suffixes import (
    learning_blocks, candidates, masked, replace_titles, title_of, plan, eligible,
)
from verify_title_release import review_text

def sample(body,subject="combined",stage="high"):
    source='<title>명일동 학원 | 이전 제목</title><main><article class="subject-main-article">'+body+'</article></main>'
    page=dict(source=source,prefix="명일동 학원",rel="sample/index.html",kind="subject",group="sample",
              stage=stage,subject=subject,blocks=learning_blocks(source,"subject"))
    page["candidates"]=candidates(page)
    return page

class TitleTests(unittest.TestCase):
    def test_title_only_and_attribute_spacing(self):
        source='<title>명일동 | 기존</title>\r\n<meta property="og:title" content = \'이전\'><meta name="description" content="기존 설명"><h1>그대로</h1>'
        updated=replace_titles(source,"명일동 | 어휘 & 복습")
        self.assertIn("content = '명일동 | 어휘 &amp; 복습'",updated)
        self.assertEqual(masked(source),masked(updated))
        self.assertEqual(title_of(updated),"명일동 | 어휘 & 복습")
        self.assertIn('<h1>그대로</h1>',updated)

    def test_wrapped_intro_priority(self):
        p=sample('<div class="subject-intro-answer"><p>긴 문장에서 핵심 구조를 놓치는 학생입니다.</p></div><section class="subject-prose-section"><p>주간 계획과 과제 분량을 정리합니다.</p></section>')
        self.assertEqual(p["blocks"][0]["weight"],6)
        self.assertGreater(p["candidates"]["긴 문장 해석"]["score"],p["candidates"]["주간 학습 흐름"]["score"])

    def test_mixed_address_keeps_learning_sentence(self):
        p=sample('<div class="subject-intro-answer"><p>첫 식을 세우지 못하는 학생입니다. 제공 주소는 서울 강동구입니다.</p></div>',"math")
        self.assertTrue(any("첫 식" in b["text"] for b in p["blocks"]))
        self.assertFalse(any("제공 주소" in b["text"] for b in p["blocks"]))

    def test_exclude_review_nav_hidden_and_facility(self):
        source='<main><article class="subject-main-article"><div class="subject-intro-answer"><p>수학은 첫 식을 세우는 과정이 중요합니다.</p></div><nav><p>분수 개념을 확인합니다.</p></nav><div style="display: none;"><p>분수 개념을 확인합니다.</p></div><section class="subject-local-context"><p>분수 개념을 확인합니다.</p></section><p>사물함과 분수 개념은 별도입니다.</p></article><section class="subject-review-section"><p>분수 개념을 확인했습니다.</p></section></main>'
        blocks=learning_blocks(source,"subject")
        self.assertTrue(blocks)
        self.assertFalse(any("분수" in b["text"] for b in blocks))

    def test_both_lead_subjects_are_reflected(self):
        p=sample('<div class="subject-intro-answer"><p>긴 문장에서 핵심 구조를 놓치고 수학은 첫 식을 세우지 못하는 학생입니다. 시험이 가까워져야 공부량을 늘립니다.</p></div>')
        plan([p])
        self.assertEqual({x["subject"] for x in p["evidence"]},{"math","english"})

    def test_opposite_subject_is_excluded(self):
        p=sample('<div class="subject-intro-answer"><p>첫 식을 세우고 검산하며 문장 구조와 독해 근거를 확인합니다.</p></div>',"math")
        self.assertTrue(p["candidates"])
        self.assertFalse(any(c["subject"]=="english" for c in p["candidates"].values()))

    def test_grade_rules(self):
        p=dict(subject="general",stage="elementary")
        self.assertFalse(eligible(p,"내신·모의고사 구분",""))
        self.assertFalse(eligible(p,"수행평가 준비",""))
        self.assertTrue(eligible(p,"숙제 시작 습관",""))

    def test_no_fabricated_fallback(self):
        p=sample('<div class="subject-intro-answer"><p>제공 주소와 등록번호만 확인합니다.</p></div>')
        self.assertFalse(p["candidates"])

    def test_name_does_not_randomize_topic(self):
        first=sample('<div class="subject-intro-answer"><p>명일동에서 긴 문장 해석과 첫 식을 세우는 과정을 확인합니다.</p></div>')
        second=sample('<div class="subject-intro-answer"><p>다른동에서 긴 문장 해석과 첫 식을 세우는 과정을 확인합니다.</p></div>')
        second["prefix"]="다른동 학원"
        plan([first,second])
        self.assertEqual(first["suffix"],second["suffix"])

    def test_general_learning_topic_is_allowed_for_math(self):
        p=sample('<div class="subject-intro-answer"><p>문항별 시간 배분을 점검하는 순서입니다.</p></div>',"math")
        plan([p])
        self.assertIn("시험 시간 배분",p["suffix"])

    def test_short_sentence_is_not_automatically_writing(self):
        p=sample('<div class="subject-intro-answer"><p>짧은 문장부터 근거를 말하게 한 뒤 지문 단위로 적용합니다.</p></div>',"english")
        self.assertNotIn("짧은 문장 쓰기",p["candidates"])

    def test_grammar_application_is_not_math_evidence(self):
        p=sample('<div class="subject-intro-answer"><p>문법 개념을 배워도 실전 문항에서 적용 순서가 흐릿한 학생입니다.</p></div>',"general")
        self.assertNotIn("개념의 문제 적용",p["candidates"])
        self.assertIn("문법의 문장 적용",p["candidates"])

    def test_display_quote_normalization(self):
        self.assertEqual(review_text("“원래의 후기입니다.”"),review_text("원래의 후기입니다."))
        self.assertNotEqual(review_text("“다른 후기입니다.”"),review_text("원래의 후기입니다."))

    def test_inner_review_punctuation_is_preserved(self):
        self.assertEqual(review_text("“학생은 ‘이유’를 설명했습니다.”"),"학생은 ‘이유’를 설명했습니다.")

if __name__=="__main__":
    unittest.main()
