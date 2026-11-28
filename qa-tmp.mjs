import { chromium } from "playwright";
const rutas = (process.argv[2] ?? "inicio").split(",");
const temas = (process.argv[3] ?? "light,dark").split(",");
const dir = "C:/Users/goliv/AppData/Local/Temp/claude/d932b45f89238748/cd5844ce-c0f6-4444-a84d-c722b919b4f1/scratchpad/qa";
const b = await chromium.launch();
for (const tema of temas) {
  const ctx = await b.newContext({ viewport:{width:390,height:900}, deviceScaleFactor:1, colorScheme: tema });
  await ctx.addInitScript(() => {
    localStorage.setItem("epic-wallet-auth", JSON.stringify({
      access_token:"t", refresh_token:"r", expires_at: Math.floor(Date.now()/1000)+99999,
      user:{ id:"u1", email:"gustavo@example.com" }}));
  });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.log("[pe]", e.message));
  await p.goto(`http://127.0.0.1:8098/index.html#/${rutas[0]}`);
  await p.waitForTimeout(1200);
  await p.evaluate(() => document.dispatchEvent(new CustomEvent("mes:cambiado",
    { detail:{ id:6, year:2026, month:10, status:"open" } })));
  await p.waitForTimeout(1800);
  for (const r of rutas) {
    await p.evaluate((h) => { location.hash = `#/${h}`; }, r);
    await p.waitForTimeout(1800);
    await p.screenshot({ path: `${dir}/${r}-${tema}.png`, fullPage: true });
  }
  await ctx.close();
}
await b.close();
console.log("ok");
