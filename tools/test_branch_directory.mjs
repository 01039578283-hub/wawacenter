import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertBranchDirectory} from '../branch-directory-check.mjs';
const name='지점안내/서울/가좌점/index.html';
const source=fs.readFileSync(new URL('../'+name,import.meta.url),'utf8');
test('source distinguishes low-grade inquiry from listed courses',()=>assert.doesNotThrow(()=>assertBranchDirectory(source,name)));
test('rejects low grades silently promoted to advertised courses',()=>assert.throws(()=>assertBranchDirectory(source.replace('data-grades="초4','data-grades="초1,초2,초3,초4'),name),/grades changed/));
test('rejects copied generic pricing without its qualification',()=>assert.throws(()=>assertBranchDirectory(source.replaceAll('지점 확정 금액 아님','등록 수강료'),name),/Generic fee/));
test('rejects accidentally collapsed consultation image',()=>assert.throws(()=>assertBranchDirectory(source.replace('height="16116"','height="16116" hidden'),name),/image must stay visible/));
test('rejects FAQ markup that overstates availability',()=>assert.throws(()=>assertBranchDirectory(source.replace('과목마다 안내 학년과 조건이 다릅니다.','모든 학년이 가능합니다.'),name),/answers and FAQ/));
test('rejects importing the reference website phone number',()=>assert.throws(()=>assertBranchDirectory(source.replaceAll('tel:01068398283','tel:01039578283'),name),/number/));

test('rejects dropping the mobile consultation image',()=>assert.throws(()=>assertBranchDirectory(source.replace(/<source[^>]+>/g,''),name),/mobile consultation image missing/));
