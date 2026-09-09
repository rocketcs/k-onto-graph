import { chromium } from "playwright";
import assert from "node:assert/strict";

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
  ]) {
    const page = await browser.newPage({ viewport });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(
      (process.env.PIPELINE_BASE_URL || "http://127.0.0.1:8013") +
        "/?workspace=enrich&view=pipeline",
    );
    const node = page.locator('.react-flow__node[data-id="parse"]');
    await node.waitFor();
    await node.scrollIntoViewIfNeeded();
    const before = await node.boundingBox();
    await page.evaluate(() => {
      window.dragProbe = {
        node: document.querySelector('.react-flow__node[data-id="parse"]'),
        canvas: document.querySelector(".react-flow__viewport"),
        frames: [],
        running: true,
      };
      const sample = () => {
        const p = window.dragProbe;
        const bounds = p.node.getBoundingClientRect();
        p.frames.push({
          x: bounds.x,
          y: bounds.y,
          connected: p.node.isConnected,
          viewport: p.canvas.style.transform,
          count: document.querySelectorAll(".react-flow__node").length,
        });
        if (p.running) requestAnimationFrame(sample);
      };
      requestAnimationFrame(sample);
    });
    for (let drag = 0; drag < 3; drag++) {
      const box = await node.boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      for (let step = 1; step <= 24; step++) {
        await page.mouse.move(
          box.x + box.width / 2 + step * 2,
          box.y + box.height / 2 - step,
        );
      }
      await page.mouse.up();
    }
    const frames = await page.evaluate(() => {
      window.dragProbe.running = false;
      return window.dragProbe.frames;
    });
    assert.ok(frames.length > 20);
    assert.ok(frames.every((f) => f.connected && f.count === 6));
    assert.equal(
      new Set(frames.map((f) => f.viewport)).size,
      1,
      "Dragging must not reset the viewport",
    );
    for (let i = 1; i < frames.length; i++) {
      assert.ok(
        Math.abs(frames[i].x - frames[i - 1].x) < 30,
        "Node must not jump or snap back",
      );
    }
    const after = await node.boundingBox();
    assert.ok(
      after.x - before.x > 100,
      "Position must survive repeated drag stops",
    );
    assert.deepEqual(errors, []);
    await page.screenshot({
      path: `../output/pipeline-workbench-e2e/drag-${viewport.width}.png`,
    });
    console.log(
      JSON.stringify({
        viewport,
        frames: frames.length,
        deltaX: after.x - before.x,
      }),
    );
    await page.close();
  }
} finally {
  await browser.close();
}
