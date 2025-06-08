window.initVisualizer = function () {
    const app = new PIXI.Application({
        width: window.innerWidth,
        height: window.innerHeight,
        resizeTo: window,
        backgroundAlpha: 0,
        view: document.getElementById('visualizer-canvas')
    });
    window.visualizerName = 'Photosynthese';

    const overlayContainer = document.getElementById("visualizer-overlay");
    if (overlayContainer) {
        // Remove any existing overlay with the specific class
        const existingOverlay = overlayContainer.querySelector(".dynamic-visualizer-overlay");
        if (existingOverlay) existingOverlay.remove();

        const overlay = document.createElement("div");
        overlay.className = "fixed top-0 left-0 w-screen h-screen bg-black/30 backdrop-blur-[60px] backdrop-saturate-150 contrast-125 z-[-1] dynamic-visualizer-overlay";
        overlayContainer.appendChild(overlay);
    }

    const bg = PIXI.Sprite.from('/static/images/cover_low.png');
    let currentArtworkUrl = '';

    bg.width = app.screen.width;
    bg.height = app.screen.height;
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
          float angle = 2.25 * sin(time + length(toCenter) * 5.0);
          float s = sin(angle);
          float c = cos(angle);
          toCenter = mat2(c, -s, s, c) * toCenter;
          uv = center + toCenter;
          vec4 color = texture2D(uSampler, uv);
          float avg = (color.r + color.g + color.b) / 3.0;
          color.rgb = mix(vec3(avg), color.rgb, 1.5);
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
    });

    updateVisualizerBackground('/static/images/cover_low.png');
};

// Auto-initialize the visualizer on initial script load
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  window.initVisualizer();
} else {
  document.addEventListener('DOMContentLoaded', () => {
    window.initVisualizer();
  });
}
