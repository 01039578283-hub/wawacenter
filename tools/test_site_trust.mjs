import assert from 'node:assert/strict';
import test from 'node:test';
import {assertTrustedHtml} from '../site-trust-check.mjs';

const ld = value => `<script type="application/ld+json">${JSON.stringify(value)}</script>`;

test('blocks the old nested three-review and five-star schema', () => {
  const old = {'@graph': [{'@type': ['EducationalOrganization', 'LocalBusiness'],
    aggregateRating: {'@type': 'AggregateRating', ratingValue: '5', ratingCount: '3'},
    review: [{'@type': 'Review', reviewBody: '공통 후기'}]}]};
  assert.throws(() => assertTrustedHtml(ld(old), 'center.html'), /center.html: review/);
});

test('blocks stars even after the JSON-LD rating was removed', () => {
  assert.throws(() => assertTrustedHtml('<div class="stars">★★★★★</div>'), /visible star/);
});

test('blocks standalone homepage reviews in a graph', () => {
  assert.throws(() => assertTrustedHtml(ld({'@graph': [
    {'@type': 'WebPage', name: '홈'},
    {'@type': 'Review', reviewRating: {'@type': 'Rating', ratingValue: '5'}}
  ]})), /review or rating/);
});

test('blocks the unverified default hours independently of reviews', () => {
  assert.throws(() => assertTrustedHtml(ld({'@type': 'LocalBusiness', openingHours: 'Mo-Sa 12:00-24:00'})), /opening hours/);
});

test('keeps normal FAQ and clearly labelled learning examples usable', () => {
  const content = '<section class="subject-review-section">상담 질문 예시: 어떤 자료를 준비하나요?</section>' +
    ld({'@type': 'FAQPage', mainEntity: [{'@type': 'Question', name: '어떤 자료가 필요한가요?', acceptedAnswer: {'@type': 'Answer', text: '최근 학습 기록을 준비하세요.'}}]});
  assert.doesNotThrow(() => assertTrustedHtml(content));
});

test('does not replace other hours with the removed default', () => {
  assert.doesNotThrow(() => assertTrustedHtml(ld({'@type': 'LocalBusiness', openingHours: 'Mo-Fr 14:00-20:00'})));
});

test('reports malformed structured data before a public build', () => {
  assert.throws(() => assertTrustedHtml("<script type='application/ld+json'>{broken}</script>"), /invalid JSON-LD/);
});
