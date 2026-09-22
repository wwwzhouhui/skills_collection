import * as THREE from 'three';
import { poem } from './poem-config';
import './poetry-page.css';

const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const audioControl = poem.audioSrc ? '<button class="narration" type="button" aria-live="polite" aria-pressed="false">朗读</button>' : '';
const sections = poem.sections.map((section, index) => `
  <section class="poetry-section ${index % 2 ? 'right' : ''}" id="${section.id}" data-scene="${index + 1}">
    <article class="poetry-card">
      <p class="index">${section.index}</p>
      <h2>${section.original}</h2>
      <p class="literal">${section.literal}</p>
      <p class="analysis">${section.analysis}</p>
    </article>
  </section>`).join('');

document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <div class="poetry-page">
    <div class="image-stage" aria-hidden="true"></div>
    <div class="poetry-tools">${audioControl}</div>
    <main>
      <section class="poetry-section hero" id="opening" data-scene="0">
        <div class="hero-copy"><p class="kicker">${poem.kicker}</p><h1>${poem.title}</h1><p>${poem.author}〔${poem.era}〕</p><blockquote>${poem.definingLine}</blockquote><p>${poem.intro}</p></div>
      </section>
      ${sections}
    </main>
    <div class="loading">正在进入诗境</div>
  </div>`;

if (poem.audioSrc) {
  const control = document.querySelector<HTMLButtonElement>('.narration')!;
  const audio = new Audio(poem.audioSrc);
  audio.preload = 'metadata';
  audio.autoplay = true;
  audio.hidden = true;
  document.body.append(audio);
  const updateAudio = (state: 'idle' | 'playing' | 'ended' | 'error') => {
    const playing = state === 'playing';
    control.classList.toggle('playing', playing);
    control.setAttribute('aria-pressed', String(playing));
    control.textContent = playing ? '暂停' : state === 'ended' ? '重播' : state === 'error' ? '音频不可用' : '朗读';
  };
  const play = async (automatic = false) => {
    try { await audio.play(); }
    catch (error) {
      if (automatic && error instanceof DOMException && error.name === 'NotAllowedError') updateAudio('idle');
      else updateAudio('error');
    }
  };
  control.addEventListener('click', () => {
    if (!audio.paused) audio.pause();
    else { if (audio.ended) audio.currentTime = 0; void play(); }
  });
  audio.addEventListener('playing', () => updateAudio('playing'));
  audio.addEventListener('pause', () => { if (!audio.ended) updateAudio('idle'); });
  audio.addEventListener('ended', () => updateAudio('ended'));
  audio.addEventListener('error', () => updateAudio('error'));
  void play(true);
}

const paths = [poem.heroImage, ...poem.sections.map((section) => section.image)];
const stage = document.querySelector<HTMLElement>('.image-stage')!;
const scene = new THREE.Scene();
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 10);
camera.position.z = 2;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
stage.append(renderer.domElement);
const manager = new THREE.LoadingManager(() => document.querySelector('.loading')?.classList.add('done'));
const loader = new THREE.TextureLoader(manager);
const textures = paths.map((path) => { const texture = loader.load(path); texture.colorSpace = THREE.SRGBColorSpace; return texture; });
const aspect = 16 / 9;
const geometry = new THREE.PlaneGeometry(aspect, 1);
const backMaterial = new THREE.MeshBasicMaterial({ map: textures[0], toneMapped: false });
const frontMaterial = new THREE.MeshBasicMaterial({ map: textures[0], toneMapped: false, transparent: true, opacity: 0 });
const back = new THREE.Mesh(geometry, backMaterial);
const front = new THREE.Mesh(geometry, frontMaterial);
front.position.z = .002;
scene.add(back, front);
let fitScale = 1, current = 0, target = 0, fade = 1;

function fit() {
  const viewport = innerWidth / innerHeight;
  camera.left = -viewport / 2; camera.right = viewport / 2; camera.top = .5; camera.bottom = -.5; camera.updateProjectionMatrix();
  fitScale = viewport >= aspect ? 1 : viewport / aspect;
  renderer.setSize(innerWidth, innerHeight);
}
function requestImage(index: number) {
  if (index === target) return;
  target = index; frontMaterial.map = textures[index]; frontMaterial.needsUpdate = true; frontMaterial.opacity = 0; fade = 0;
}
function update() {
  const nodes = [...document.querySelectorAll<HTMLElement>('.poetry-section')];
  let active = nodes[0], distance = Infinity;
  nodes.forEach((node) => { const value = Math.abs(node.getBoundingClientRect().top - innerHeight * .3); if (value < distance) { active = node; distance = value; } });
  nodes.forEach((node) => node.classList.toggle('active', node === active));
  requestImage(Number(active.dataset.scene || 0));
}
addEventListener('scroll', update, { passive: true });
addEventListener('resize', fit);
const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  const delta = Math.min(clock.getDelta(), .04);
  back.scale.setScalar(fitScale); front.scale.setScalar(fitScale);
  if (current !== target) { fade = THREE.MathUtils.damp(fade, 1, reducedMotion ? 24 : 3.2, delta); frontMaterial.opacity = fade; if (fade > .995) { current = target; backMaterial.map = textures[current]; backMaterial.needsUpdate = true; frontMaterial.opacity = 0; } }
  renderer.render(scene, camera);
}
fit(); update(); requestAnimationFrame(frame);
