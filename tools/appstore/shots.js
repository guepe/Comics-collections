// Captures App Store : node shots.js [nom1 nom2 ...]
const { chromium } = require("playwright");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const BASE = "http://127.0.0.1:8075";
const OUT = path.join(__dirname, "out", "raw");
fs.mkdirSync(OUT, { recursive: true });
const IDS = JSON.parse(fs.readFileSync(path.join(__dirname, "ids.json")));
const only = process.argv.slice(2);
const want = (n) => !only.length || only.includes(n);
const A = (xmlid) => `${BASE}/odoo/action-comics_collections.${xmlid}`;

const HIDE_CSS = `
  .o_notification_manager, .o_notification, .o-mail-ChatWindowContainer, .o_debug_manager,
  .o_cookies_discrete, #website_cookies_bar, .o_livechat_button, .o-livechat-LivechatButton,
  .o_website_edit_in_backend, .o_frontend_to_backend_nav, .o_we_website_top_actions,
  .o-mail-ChatHub, .o_menu_systray .badge, header a[href^="tel:"] { display: none !important; }
  * { caret-color: transparent !important; }
`;

async function settle(page, extra = 600) {
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForFunction(() => !document.querySelector(".o_loading_indicator, .o_blockUI"), null, { timeout: 15000 }).catch(() => {});
  // images chargées
  await page.waitForFunction(() => [...document.images].every((i) => i.complete || i.loading === "lazy"), null, { timeout: 6000 }).catch(() => {});
  await page.addStyleTag({ content: HIDE_CSS }).catch(() => {});
  await page.waitForTimeout(extra);
}

async function shot(page, name, opts = {}) {
  await settle(page, opts.wait || 800);
  const file = path.join(OUT, name + ".png");
  if (opts.selector) {
    await page.locator(opts.selector).first().screenshot({ path: file });
  } else if (opts.fullPage) {
    const h = await page.evaluate(() => { const f = document.querySelector("footer#bottom, footer");
      return f ? f.getBoundingClientRect().top + window.scrollY : document.documentElement.scrollHeight; });
    await page.screenshot({ path: file, clip: { x: 0, y: 0, width: 1440, height: Math.min(h, opts.maxHeight || 1500) }, fullPage: true });
  } else {
    await page.screenshot({ path: file });
  }
  console.log("OK", name);
}

async function login(context, login, password) {
  const page = await context.newPage();
  await page.goto(`${BASE}/web/login?db=appstore_demo`);
  await page.fill("input[name=login]", login);
  await page.fill("input[name=password]", password);
  await page.locator("form.oe_login_form button[type=submit], .oe_login_buttons button[type=submit]").first().click();
  await page.waitForURL((u) => !u.pathname.startsWith("/web/login"), { timeout: 90000 }).catch(async (e) => {
    await page.screenshot({ path: path.join(OUT, "login_fail.png") }); throw e; });
  await settle(page);
  return page;
}

async function doAction(page, model, resId, name) {
  await page.evaluate(
    ([m, id, n]) =>
      odoo.__WOWL_DEBUG__.root.env.services.action.doAction({
        type: "ir.actions.act_window", res_model: m, res_id: id, name: n, views: [[false, "form"]], target: "new",
      }),
    [model, resId, name]
  );
  await page.waitForSelector(".modal .o_form_view", { timeout: 15000 });
  await page.waitForTimeout(800);
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
}

async function run(name, fn) {
  if (!want(name)) return;
  try { await fn(); } catch (e) { console.log("FAIL", name, e.message.split("\n")[0]); }
}

(async () => {
  const browser = await chromium.launch();
  const mk = () => browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, colorScheme: "light", locale: "fr-BE" });

  // ── Back-office (admin) ─────────────────────────────────────────────
  const adminCtx = await mk();
  const p = await login(adminCtx, "admin", "admin");

  await run("screenshot_dashboard", async () => { await p.goto(A("action_comic_collection_dashboard")); await shot(p, "screenshot_dashboard", { wait: 1500 }); });
  await run("screenshot_series", async () => { await p.goto(A("action_comic_serie")); await shot(p, "screenshot_series"); });
  await run("screenshot_albums", async () => { await p.goto(A("action_comic_work")); await shot(p, "screenshot_albums"); });
  await run("screenshot_album_form", async () => { await p.goto(A("action_comic_work") + "/" + IDS.work_album); await shot(p, "screenshot_album_form"); });
  await run("screenshot_serie_form", async () => { await p.goto(A("action_comic_serie") + "/" + IDS.serie_form); await settle(p);
    await p.locator(".o_notebook .nav-link", { hasText: "Albums" }).first().click(); await shot(p, "screenshot_serie_form"); });
  await run("screenshot_wishlist", async () => { await p.goto(`${BASE}/odoo/action-comics_collections.action_comic_wishlist`); await settle(p);
    for (let i = 0; i < 4; i++) { await p.locator(".o_group_header").nth(i).click(); await p.waitForTimeout(700); }
    await shot(p, "screenshot_wishlist"); });
  await run("screenshot_library", async () => { await p.goto(A("action_comic_my_library")); await shot(p, "screenshot_library"); });
  await run("screenshot_author", async () => {
    await p.goto(A("action_comic_auteurs") + "/" + IDS.author);
    await settle(p);
    const tab = p.locator(".o_notebook .nav-link", { hasText: "Biographie" });
    if (await tab.count()) await tab.first().click();
    await p.setViewportSize({ width: 1440, height: 1240 });
    await shot(p, "screenshot_author");
    await p.setViewportSize({ width: 1440, height: 900 });
  });
  await run("screenshot_import", async () => {
    await p.goto(A("action_comic_collection_dashboard")); await settle(p);
    await doAction(p, "comic.import.wizard", IDS.import_wizard, "Import CSV / Excel");
    await shot(p, "screenshot_import");
  });
  await run("screenshot_ai_wizard", async () => {
    await p.goto(A("action_comic_work") + "/" + IDS.work_ai); await settle(p);
    await doAction(p, "comic.ai.wizard", IDS.ai_wizard, "Assistant IA — synopsis");
    await shot(p, "screenshot_ai_wizard");
  });
  await run("shop_release_notify", async () => {
    await p.goto(`${BASE}/odoo/comic.edition/${IDS.nebula8_edition}`); await settle(p);
    await doAction(p, "comic.release.notify.wizard", IDS.rel_wizard, "Prévenir les clients");
    await shot(p, "shop_release_notify");
  });

  // ── Portail (Camille) ───────────────────────────────────────────────
  const camCtx = await mk();
  const c = await login(camCtx, "camille", "camille");
  await run("shop_product", async () => { await c.goto(`${BASE}/shop/album-${IDS.product_page}`); await shot(c, "shop_product", { fullPage: true, maxHeight: 1100 }); });
  await run("shop_series", async () => { await c.goto(`${BASE}/shop/series/${IDS.shop_serie}`); await shot(c, "shop_series", { fullPage: true, maxHeight: 1300 }); });
  await run("shop_portal_library", async () => { await c.goto(`${BASE}/my/library`); await shot(c, "shop_portal_library", { fullPage: true, maxHeight: 1400 }); });
  await run("shop_portal_dashboard", async () => { await c.goto(`${BASE}/my/library/dashboard`); await shot(c, "shop_portal_dashboard", { fullPage: true, maxHeight: 1400 }); });
  await run("shop_portal_add", async () => { await c.goto(`${BASE}/my/library/add`); await shot(c, "shop_portal_add", { fullPage: true, maxHeight: 1100 }); });
  await run("shop_portal_discover", async () => {
    const sid = (await camCtx.cookies()).find((k) => k.name === "session_id").value;
    const py = `import json,glob;f=[x for x in glob.glob('/var/lib/odoo/sessions/*/*') if x.endswith('${sid}')][0];d=json.load(open(f));d['comic_ai_discovery_wizard_id']=${IDS.disc_wizard};json.dump(d,open(f,'w'));print(f)`;
    console.log(execSync(`${process.env.HOME}/.docker/bin/docker exec appstore-odoo python3 -c "${py}"`).toString().trim());
    await c.goto(`${BASE}/my/library/discover`);
    await shot(c, "shop_portal_discover", { fullPage: true, maxHeight: 1500 });
  });

  // ── Public ──────────────────────────────────────────────────────────
  const pubCtx = await mk();
  const q = await pubCtx.newPage();
  await run("shop_wishlist_public", async () => { await q.goto(`${BASE}/wishlist/${IDS.token}`); await shot(q, "shop_wishlist_public", { fullPage: true, maxHeight: 1300 }); });

  await browser.close();
})();
