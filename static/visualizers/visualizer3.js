window.initVisualizer = function () {
const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    resizeTo: window,
    backgroundAlpha: 0,
    view: document.getElementById('visualizer-canvas')
});

    window.visualizerName = 'Kimono';


// Ensure only one overlay is present and prevent compounding effects
const container = document.getElementById("visualizer-overlay");
const existingOverlay = container?.querySelector(".dynamic-visualizer-overlay");
if (existingOverlay) existingOverlay.remove();

const overlay = document.createElement("div");
overlay.className = "fixed top-0 left-0 w-screen h-screen bg-black/50 backdrop-blur-[50px] backdrop-saturate-200 contrast-125 z-[-1] dynamic-visualizer-overlay";
container?.appendChild(overlay);

const bg = PIXI.Sprite.from('/static/images/cover_low.png');
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
currentArtworkUrl = '/static/images/cover_low.png';
const freshBaseTexture = PIXI.BaseTexture.from(`${currentArtworkUrl}?ts=${Date.now()}`);
const freshTexture = new PIXI.Texture(freshBaseTexture);
bg.texture = freshTexture;
updateVisualizerBackground(currentArtworkUrl);
app.stage.addChild(bg);

const fragmentShader = `
  precision mediump float;
  varying vec2 vTextureCoord;
  uniform sampler2D uSampler;
  uniform float time;

  void main(void) {
    vec2 uv = vTextureCoord;
    vec2 center = vec2(0.5, 0.5);
    vec2 toCenter = uv - center;

    // Radial distortion
    float distortion = 0.5 * sin(10.0 * length(toCenter) - time * 2.0);
    uv += toCenter * distortion;

    // Chromatic aberration
    float angle = time * 1.5;
    float rOffset = 0.012 * sin(angle);
    float gOffset = 0.012 * cos(angle);
    float bOffset = -0.02 * sin(angle * 0.5);

    vec4 r = texture2D(uSampler, uv + rOffset * toCenter);
    vec4 g = texture2D(uSampler, uv + gOffset * toCenter);
    vec4 b = texture2D(uSampler, uv + bOffset * toCenter);

    vec4 color = vec4(r.r, g.g, b.b, 1.0);

    gl_FragColor = color;
  }
`;

const filter = new PIXI.Filter(undefined, fragmentShader, { time: 0 });
bg.filters = [filter];

function updateVisualizerBackground(newUrl) {
    if (newUrl === currentArtworkUrl) return;

    currentArtworkUrl = newUrl;
    const freshBaseTexture = PIXI.BaseTexture.from(`${newUrl}?ts=${Date.now()}`);
    const freshTexture = new PIXI.Texture(freshBaseTexture);
    bg.texture = freshTexture;
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