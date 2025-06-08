window.initVisualizer = function () {
  const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    resizeTo: window,
    backgroundAlpha: 0,
    view: document.getElementById('visualizer-canvas'),
  });

  window.visualizerName = 'Spotlights';

  const container = document.getElementById("visualizer-overlay");
  const existingOverlay = container?.querySelector(".dynamic-visualizer-overlay");
  if (existingOverlay) existingOverlay.remove();

  const overlay = document.createElement("div");
  overlay.className =
    "fixed top-0 left-0 w-screen h-screen  backdrop-blur-[50px] backdrop-saturate-150 z-[-1] dynamic-visualizer-overlay";
  container?.appendChild(overlay);

  const textureUrl = '/static/images/cover_low.png';
  const texture = PIXI.Texture.from(`${textureUrl}?ts=${Date.now()}`);
  const sausage = new PIXI.Sprite(texture);

  // Stretch to sausage shape
  sausage.anchor.set(0.5);
  sausage.width = app.screen.width * 1.5;
  sausage.height = app.screen.height * 0.15;
  sausage.x = -sausage.width / 2;
  sausage.y = app.screen.height / 2;

  app.stage.addChild(sausage);

  // All sausages share the same texture instance (no clone)
  const sausage2 = new PIXI.Sprite(texture);
  const sausage3 = new PIXI.Sprite(texture);

  for (const s of [sausage2, sausage3]) {
    s.anchor.set(0.5);
    s.width = sausage.width;
    s.height = sausage.height;
    app.stage.addChild(s);
  }

  window.updateVisualizerBackground = function (newUrl) {
    const updatedTexture = PIXI.Texture.from(`${newUrl}?ts=${Date.now()}`);
    sausage.texture = updatedTexture;
    sausage2.texture = updatedTexture;
    sausage3.texture = updatedTexture;
  };

  let t = 0;

  app.ticker.add((delta) => {
    t += 0.01 * delta;

    const radius = Math.min(app.screen.width, app.screen.height) * 0.35;
    const centerX = app.screen.width / 2;
    const centerY = app.screen.height / 2;

    // Make the sausage move in a looping/lapping sinusoidal orbit with a subtle wobble
    const wobble = 100;
    sausage.x = centerX + radius * Math.cos(t) * Math.sin(t * 0.7) + Math.sin(t * 3) * wobble;
    sausage.y = centerY + radius * Math.sin(t) * Math.cos(t * 0.5) + Math.cos(t * 2) * wobble;

    sausage.rotation = Math.atan2(
      radius * Math.cos(t) * Math.cos(t * 0.5) + radius * Math.sin(t) * Math.sin(t * 0.5),
      -radius * Math.sin(t) * Math.sin(t * 0.7) + radius * Math.cos(t) * Math.cos(t * 0.7)
    );

    const t2 = t + 2;
    const t3 = t + 4;

    sausage2.x = centerX + radius * Math.cos(t2) * Math.sin(t2 * 0.7) + Math.sin(t2 * 3) * wobble;
    sausage2.y = centerY + radius * Math.sin(t2) * Math.cos(t2 * 0.5) + Math.cos(t2 * 2) * wobble;
    sausage2.rotation = Math.atan2(
      radius * Math.cos(t2) * Math.cos(t2 * 0.5) + radius * Math.sin(t2) * Math.sin(t2 * 0.5),
      -radius * Math.sin(t2) * Math.sin(t2 * 0.7) + radius * Math.cos(t2) * Math.cos(t2 * 0.7)
    );

    sausage3.x = centerX + radius * Math.cos(t3) * Math.sin(t3 * 0.7) + Math.sin(t3 * 3) * wobble;
    sausage3.y = centerY + radius * Math.sin(t3) * Math.cos(t3 * 0.5) + Math.cos(t3 * 2) * wobble;
    sausage3.rotation = Math.atan2(
      radius * Math.cos(t3) * Math.cos(t3 * 0.5) + radius * Math.sin(t3) * Math.sin(t3 * 0.5),
      -radius * Math.sin(t3) * Math.sin(t3 * 0.7) + radius * Math.cos(t3) * Math.cos(t3 * 0.7)
    );
  });
};

if (document.readyState === 'complete' || document.readyState === 'interactive') {
  window.initVisualizer?.();
} else {
  document.addEventListener('DOMContentLoaded', () => {
    window.initVisualizer?.();
  });
}