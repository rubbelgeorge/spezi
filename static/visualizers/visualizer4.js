window.initVisualizer = function () {
const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    resizeTo: window,
    backgroundAlpha: 0,
    view: document.getElementById('visualizer-canvas')
});

    window.visualizerName = 'Simon';


// Ensure only one overlay is present and prevent compounding effects
const container = document.getElementById("visualizer-overlay");
const existingOverlay = container?.querySelector(".dynamic-visualizer-overlay");
if (existingOverlay) existingOverlay.remove();

const overlay = document.createElement("div");
overlay.className = "fixed top-0 left-0 w-screen h-screen bg-black/50 backdrop-blur-[50px] backdrop-saturate-150 contrast-125 z-[-1] dynamic-visualizer-overlay";
container?.appendChild(overlay);

const bg = PIXI.Sprite.from('/static/images/cover.png');
bg.anchor.set(0.5);
bg.x = app.screen.width / 2;
bg.y = app.screen.height / 2;
// bg.rotation = Math.PI / 2;
// Resize to cover screen while preserving aspect ratio
const textureRatio = bg.texture.width / bg.texture.height;
const screenRatio = app.screen.width / app.screen.height;

if (textureRatio > screenRatio) {
  bg.height = app.screen.height;
  bg.width = bg.height * textureRatio;
} else {
  bg.width = app.screen.width;
  bg.height = bg.width / textureRatio;
}
let currentArtworkUrl = '';
currentArtworkUrl = '/static/images/cover.png';
const texture = PIXI.Texture.from(`${currentArtworkUrl}?ts=${Date.now()}`);
bg.texture = texture;
app.stage.addChild(bg);

const fragmentShader = `
  precision mediump float;
  varying vec2 vTextureCoord;
  uniform sampler2D uSampler;
  uniform float time;

  float pattern(vec2 uv) {
    return sin(10.0 * uv.x + time) + cos(10.0 * uv.y - time);
  }

  float radialBurst(vec2 uv, vec2 center, float t) {
    vec2 diff = uv - center;
    float r = length(diff);
    float a = atan(diff.y, diff.x);
    float burst = sin(20.0 * r - t * 6.0) * 0.5 + 0.5;
    float radial = pow(1.0 - r, 3.0) * burst;
    float rays = abs(sin(a * 10.0 + t * 3.0)) * 0.2;
    return clamp(radial + rays, 0.0, 1.0);
  }

  float transformPulse(vec2 uv, vec2 center, float t, float intensity) {
    float d = distance(uv, center);
    float pulse = sin(20.0 * d - t * 5.0) * 0.5 + 0.5;
    return smoothstep(0.3, 0.0, d) * pulse * intensity;
  }

  void main(void) {
    vec2 uv = vTextureCoord;

    vec2 t1 = vec2(fract(sin(time * 0.6) * 43758.5453), fract(cos(time * 0.9) * 24682.1234));
    vec2 t2 = vec2(fract(sin(time * 1.2) * 93721.1645), fract(cos(time * 1.4) * 57412.7623));
    vec2 t3 = vec2(fract(sin(time * 1.8) * 38711.4321), fract(cos(time * 2.0) * 87123.9832));

    float tp1 = transformPulse(uv, t1, time, 0.05);
    float tp2 = transformPulse(uv, t2, time, 0.03);
    float tp3 = transformPulse(uv, t3, time, 0.04);

    uv += (uv - t1) * tp1;
    uv += (uv - t2) * tp2;
    uv += (uv - t3) * tp3;

    vec2 center = vec2(0.5);
    vec2 pos = uv - center;

    float radius = length(pos);
    float angle = atan(pos.y, pos.x);

    // Spiral warping
    angle += 0.3 * sin(radius * 8.0 - time * 4.0);
    radius *= 1.0 + 0.1 * sin(time + radius * 12.0);

    pos = vec2(cos(angle), sin(angle)) * radius;
    uv = center + pos;

    // Pulsating distortion
    uv += 0.03 * vec2(
      sin(25.0 * uv.y + time * 1.5),
      cos(25.0 * uv.x + time * 1.3)
    );

    // Per-channel UV shifts
    float shift = 0.01 + 0.005 * sin(time);
    vec4 r = texture2D(uSampler, uv + vec2(shift, 0.0));
    vec4 g = texture2D(uSampler, uv);
    vec4 b = texture2D(uSampler, uv - vec2(shift, 0.0));
    vec4 color = vec4(r.r, g.g, b.b, 1.0);

    // Vignette
    float vignette = smoothstep(0.9, 0.4 + 0.1 * sin(time), radius);
    color.rgb *= vignette;

    float s = radialBurst(uv, vec2(0.5), time);

    // Pattern enhancement
    color.rgb += 0.05 * pattern(uv + 0.5 * sin(time * 0.7));
    color.rgb += vec3(1.0, 0.5, 0.2) * s;

    gl_FragColor = color;
  }
`;

const filter = new PIXI.Filter(undefined, fragmentShader, { time: 0 });
bg.filters = [filter];

function updateVisualizerBackground(newUrl) {
    if (newUrl === currentArtworkUrl) return;

    currentArtworkUrl = newUrl;
    const texture = PIXI.Texture.from(`${newUrl}?ts=${Date.now()}`);
    bg.texture = texture;
}

window.updateVisualizerBackground = updateVisualizerBackground;

app.ticker.add((delta) => {
    filter.uniforms.time += 0.003 * delta;
    bg.rotation += 0.001 * delta;
});
}
// Auto-initialize the visualizer on initial script load
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  window.initVisualizer?.();
} else {
  document.addEventListener('DOMContentLoaded', () => {
    window.initVisualizer?.();
  });
}