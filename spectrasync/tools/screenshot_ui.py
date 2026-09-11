"""Screenshot the running UI.  python tools/screenshot_ui.py [port] [outdir]"""
import sys, time
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "8555"
OUT = sys.argv[2] if len(sys.argv) > 2 else "outputs"
PAGES = ["1. Translation", "2. Rotation & Scale", "3. Stacking",
         "4. Object Removal", "5. Highlight", "6. How it works"]

def settle(page, timeout=90):
    """Wait until Streamlit stops showing its running indicator."""
    t0 = time.time()
    time.sleep(2.0)
    while time.time() - t0 < timeout:
        running = page.locator('[data-testid="stStatusWidget"]').count()
        skeleton = page.locator('.stSkeleton, [data-testid="stSkeleton"]').count()
        if running == 0 and skeleton == 0:
            time.sleep(1.5)
            return True
        time.sleep(1.0)
    return False

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1680, "height": 1150},
                    device_scale_factor=2)
    pg.goto(f"http://localhost:{PORT}", wait_until="networkidle", timeout=120000)
    settle(pg)
    for i, label in enumerate(PAGES, 1):
        try:
            pg.get_by_text(label, exact=True).first.click(timeout=15000)
        except Exception as e:
            print(f"  could not select {label}: {e}")
            continue
        settle(pg)
        path = f"{OUT}/ui_{i}_{label.split('. ')[1].lower().replace(' ', '_').replace('&','and')}.png"
        pg.screenshot(path=path, full_page=True)
        print("saved", path)
    b.close()
