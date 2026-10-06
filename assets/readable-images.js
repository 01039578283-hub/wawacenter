/* Progressive enhancement: a normal image link still works without JavaScript. */
(() => {
  let reader, image, scroller, title, toggle, hint, opener;
  function prepare() {
    reader = document.createElement('dialog');
    reader.className = 'image-reader';
    reader.setAttribute('aria-labelledby', 'image-reader-title');
    reader.innerHTML = '<div class="image-reader-header"><h2 class="image-reader-title" id="image-reader-title">이미지 확대</h2><div class="image-reader-controls"><button type="button" data-reader-fit>화면에 맞추기</button><button type="button" data-reader-close>닫기</button></div></div><p class="image-reader-hint">원본 크기입니다. 좌우·위아래로 움직여 작은 글씨를 읽어 보세요.</p><div class="image-reader-scroll" tabindex="0" aria-label="확대 이미지, 좌우와 위아래로 스크롤"><img alt=""></div>';
    document.body.append(reader);
    title = reader.querySelector('h2');
    image = reader.querySelector('img');
    scroller = reader.querySelector('.image-reader-scroll');
    toggle = reader.querySelector('[data-reader-fit]');
    hint = reader.querySelector('.image-reader-hint');
    toggle.addEventListener('click', () => {
      const fit = scroller.dataset.fit !== 'true';
      scroller.dataset.fit = String(fit);
      toggle.textContent = fit ? '원본 크기로 보기' : '화면에 맞추기';
      hint.textContent = fit ? '화면에 맞춘 크기입니다. 작은 글씨는 원본 크기로 바꾸어 읽어 보세요.' : '원본 크기입니다. 좌우·위아래로 움직여 작은 글씨를 읽어 보세요.';
    });
    reader.querySelector('[data-reader-close]').addEventListener('click', () => reader.close());
    reader.addEventListener('close', () => {
      image.removeAttribute('src');
      opener?.focus();
    });
  }
  document.addEventListener('click', event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest?.('a.readable-image');
    if (!anchor || typeof HTMLDialogElement === 'undefined' || typeof HTMLDialogElement.prototype.showModal !== 'function') return;
    const preview = anchor.querySelector('img');
    if (!preview) return;
    event.preventDefault();
    if (!reader) prepare();
    opener = anchor;
    title.textContent = anchor.dataset.imageKind === 'map' ? '지점 지도 확대' : '수업 안내 이미지 확대';
    image.alt = preview.alt;
    image.width = Number(preview.getAttribute('width')) || preview.naturalWidth;
    image.height = Number(preview.getAttribute('height')) || preview.naturalHeight;
    image.style.setProperty('--image-native-width', `${image.width}px`);
    image.src = anchor.href;
    scroller.dataset.fit = 'false';
    toggle.textContent = '화면에 맞추기';
    hint.textContent = '원본 크기입니다. 좌우·위아래로 움직여 작은 글씨를 읽어 보세요.';
    reader.showModal();
    scroller.scrollTop = 0;
    scroller.scrollLeft = 0;
    reader.querySelector('[data-reader-close]').focus();
  });
})();
