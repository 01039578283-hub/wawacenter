# 동네별 초·중·고와 영어·수학 안내

현재 구조는 `/지점안내/지역/실제지점/CSV동네명중학생학원/수학/`이다.
CSV의 `근처 수업가능 동네`를 제목에 그대로 쓰고, URL에서는 공백을 제거한다.
`센터명`으로 기존 실제 지점에 연결한다. 서로 다른 동네의 원고를 합치지 않는다.
초·중·고 ZIP 9개와 학년별 영어·수학 ZIP 12개를 다시 읽어 같은 동네·유형의
여러 원고를 상담 기준과 학습 점검 내용으로 보완한다.

1. 외부 검증 폴더에 현재 public manifest, public source ZIP과 각 JSON 데이터의
   `before-` 사본을 보관한다. 원본 작업 폴더의 미커밋 변경은 건드리지 않는다.
2. `prepare_neighborhood_directory.py --csv <센터정보 정리.csv> --sources <홈페이지 작업 폴더> --audit <검증 폴더>`
3. `rebuild_neighborhood_directory.py --audit <검증 폴더>`
4. `audit_neighborhood_directory.py source --csv <CSV> --audit <검증 폴더>`와
   `node --test tools/test_*.mjs`를 실행한다.
5. `release-public-build.mjs`, `wawa-analytics-build.mjs wawa-07 .public-release`,
   `seo-descriptions.mjs --root=.public-release`를 순서대로 실행한다.
6. `audit_neighborhood_directory.py public --audit <검증 폴더>`로 전체 출력과
   내부링크·앵커·사이트맵·canonical을 검증한다. 로컬 HTTP와 모바일 화면도 확인한다.
7. 승인된 배포 후 `audit_neighborhood_directory.py http --base <운영 도메인> --audit <검증 폴더>`로
   새 페이지와 기존 주소의 301 응답을 확인한다. 실패만 재검사할 때는 `--retry`를 쓴다.
8. 실제 운영 사이트맵과 일치하는 이번 재구성 주소 3,339개를 깊이 순서로 정렬해,
   한글 URL 한 줄당 하나인 UTF-8 BOM/CRLF TXT로 바탕화면에 저장한다.

지점·지역 허브는 유지한다. 잘못 합쳐진 1,692개 학년·과목 주소는 영구 이동한다.
여러 동네가 연결된 지점의 이전 주소는 지점의 동네 선택 영역으로 안내하고,
한 동네만 연결된 경우 해당 동네 페이지로 직접 안내한다. 과거 동네 허브는
다시 만들지 않는다. 이전 동네별 학년 주소 1,113개도 새 주소로 한 번에 연결한다.
Vercel 규칙은 동네별/지점별 매개변수 패턴으로 747개를 사용하며,
2,805개 기존 주소의 두 trailing slash 변형을 모두 검사한다.

교육비·개설 학년·주소·등록·사진·교사 데이터는 기존 검토 자료를 유지한다.
확인되지 않은 개설·성과·시설·후기를 원고에서 운영 사실로 옮기지 않는다.
긴 상담 이미지와 모바일 이미지, 공통 메뉴, 교재·학습가이드·선생님 링크도 유지한다.
이전 개별 build/prepare 스크립트의 main 함수는 과거 구조의 기록이다.
이번 구조에는 위의 neighborhood 스크립트를 사용한다.
