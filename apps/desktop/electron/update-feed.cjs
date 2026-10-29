// Release feed: finds a newer GitHub release and downloads its signed assets.
// Downloads are only staged here; update-security.cjs still verifies the
// Ed25519 manifest and SHA-256 before anything can be installed.
const fs = require("node:fs");
const path = require("node:path");
const { newer } = require("./update-security.cjs");

const FEED =
  process.env.ALT_UPDATE_FEED ||
  "https://api.github.com/repos/caio306santana/ALT-/releases/latest";
const HOSTS = new Set([
  "api.github.com",
  "github.com",
  "objects.githubusercontent.com",
  "release-assets.githubusercontent.com",
]);
const HEADERS = {
  Accept: "application/vnd.github+json",
  "User-Agent": "ALT-AI-updater",
};

function trusted(url) {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || !HOSTS.has(parsed.hostname))
    throw new Error("Endereço de atualização fora do GitHub");
  return parsed.href;
}

function parseRelease(release, currentVersion) {
  if (!release || release.draft || release.prerelease) return null;
  const version = String(release.tag_name || "").replace(/^v/, "");
  if (!/^\d+\.\d+\.\d+$/.test(version) || !newer(version, currentVersion))
    return null;
  const assets = Array.isArray(release.assets) ? release.assets : [];
  const installer = assets.find(
    (a) => a.name === `ALT-AI-Setup-${version}-x64.exe`,
  );
  const manifest = assets.find((a) => a.name === `ALT-AI-${version}-update.json`);
  return {
    version,
    name: String(release.name || "ALT-AI " + version).slice(0, 200),
    notes: String(release.body || "").slice(0, 20000),
    published_at: String(release.published_at || ""),
    page: trusted(release.html_url || "https://github.com/"),
    downloadable: !!(installer && manifest),
    installer: installer
      ? { name: installer.name, size: installer.size, url: trusted(installer.browser_download_url) }
      : null,
    manifest: manifest
      ? { name: manifest.name, size: manifest.size, url: trusted(manifest.browser_download_url) }
      : null,
  };
}

async function checkRelease(currentVersion, fetcher = fetch) {
  const response = await fetcher(trusted(FEED), { headers: HEADERS });
  if (response.status === 404)
    return {
      available: false,
      reason:
        "Nenhuma release pública encontrada. Releases de repositório privado não são visíveis ao aplicativo sem login.",
    };
  if (!response.ok)
    return { available: false, reason: `GitHub respondeu ${response.status}. Tente mais tarde.` };
  const release = parseRelease(await response.json(), currentVersion);
  return release ? { available: true, ...release } : { available: false, reason: "Você já está na versão mais recente." };
}

async function download(url, destination, maxBytes, onProgress, fetcher = fetch) {
  const response = await fetcher(trusted(url), { headers: { "User-Agent": HEADERS["User-Agent"] } });
  if (!response.ok || !response.body) throw new Error("Falha ao baixar a atualização");
  trusted(response.url || url);
  const partial = destination + ".partial";
  const file = fs.createWriteStream(partial, { flags: "w" });
  await new Promise((resolve, reject) => {
    file.once("open", resolve);
    file.once("error", reject);
  });
  let received = 0;
  try {
    for await (const chunk of response.body) {
      received += chunk.length;
      if (received > maxBytes) throw new Error("Arquivo maior que o informado pela release");
      if (!file.write(chunk)) await new Promise((r) => file.once("drain", r));
      if (onProgress) onProgress(received);
    }
    await new Promise((resolve, reject) => file.end((e) => (e ? reject(e) : resolve())));
    fs.renameSync(partial, destination);
    return received;
  } catch (error) {
    await new Promise((resolve) => {
      file.once("close", resolve);
      file.destroy();
    });
    fs.rmSync(partial, { force: true });
    throw error;
  }
}

async function stageRelease(info, folder, onProgress, fetcher = fetch) {
  if (!info || !info.downloadable) throw new Error("A release não contém instalador e manifesto assinados");
  fs.mkdirSync(folder, { recursive: true });
  for (const old of fs.readdirSync(folder)) fs.rmSync(path.join(folder, old), { force: true });
  const manifestPath = path.join(folder, path.basename(info.manifest.name));
  await download(info.manifest.url, manifestPath, 32000, null, fetcher);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const expected = manifest?.payload?.size;
  if (!Number.isSafeInteger(expected) || expected <= 0 || expected > 2 * 1024 ** 3)
    throw new Error("Manifesto de atualização inválido");
  const installerPath = path.join(folder, path.basename(String(manifest.payload.file)));
  await download(info.installer.url, installerPath, expected, (received) => onProgress && onProgress(received, expected), fetcher);
  return { manifest, installerPath };
}

module.exports = { FEED, checkRelease, parseRelease, stageRelease, trusted };
