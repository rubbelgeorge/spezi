window.initVisualizer = function () {
  const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    resizeTo: window,
    backgroundAlpha: 0,
    view: document.getElementById('visualizer-canvas'),
  });

  window.visualizerName = 'Cover Rain';

  const container = document.getElementById("visualizer-overlay");
  const existingOverlay = container?.querySelector(".dynamic-visualizer-overlay");
  if (existingOverlay) existingOverlay.remove();

  const overlay = document.createElement("div");
  overlay.className =
    "fixed top-0 left-0 w-screen h-screen backdrop-blur-[20px] backdrop-saturate-200 z-[-1] dynamic-visualizer-overlay";
  container?.appendChild(overlay);

  const textureUrl = '/static/images/cover.png';
  const baseTexture = PIXI.BaseTexture.from(`${textureUrl}?ts=${Date.now()}`);
  const texture = new PIXI.Texture(baseTexture);
  let currentTexture = texture;
  window.updateVisualizerBackground?.(textureUrl);

  const circles = [];
  const maxCircles = 30;

  function createCircle() {
    const circle = new PIXI.Sprite(currentTexture);
    circle.anchor.set(0.5);
    const size = 50 + Math.random() * 30;
    circle.width = circle.height = size;
    circle.x = Math.random() * app.screen.width;
    circle.y = -size;
    circle.vy = 1 + Math.random() * 3;
    circle.vx = (Math.random() - 0.5) * 0.5;
    circle.rotationSpeed = (Math.random() - 0.5) * 0.05;

    // Mask to circle shape
    const mask = new PIXI.Graphics();
    mask.beginFill(0xffffff);
    mask.drawCircle(0, 0, size / 2);
    mask.endFill();
    circle.mask = mask;
    mask.x = circle.x;
    mask.y = circle.y;
    app.stage.addChild(mask);

    app.stage.addChild(circle);
    circles.push({ sprite: circle, mask });
  }

  app.ticker.add((delta) => {
    if (circles.length < maxCircles && Math.random() < 0.1) {
      createCircle();
    }

    for (const { sprite, mask } of circles) {
      sprite.y += sprite.vy * delta;
      sprite.x += sprite.vx * delta;
      sprite.rotation += sprite.rotationSpeed * delta;

      mask.x = sprite.x;
      mask.y = sprite.y;
    }

    // Remove circles off screen
    for (let i = circles.length - 1; i >= 0; i--) {
      if (circles[i].sprite.y - circles[i].sprite.height > app.screen.height) {
        app.stage.removeChild(circles[i].sprite);
        app.stage.removeChild(circles[i].mask);
        circles.splice(i, 1);
      }
    }
  });

  window.updateVisualizerBackground = function (newUrl) {
    const updatedTexture = PIXI.Texture.from(`${newUrl}?ts=${Date.now()}`);
    currentTexture = updatedTexture;
  };
};

if (document.readyState === 'complete' || document.readyState === 'interactive') {
  window.initVisualizer?.();
} else {
  document.addEventListener('DOMContentLoaded', () => {
    window.initVisualizer?.();
  });
}