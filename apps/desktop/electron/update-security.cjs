const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
function versionNumber(value) {
  if (!/^\d+\.\d+\.\d+$/.test(value))
    throw new Error("Versão de atualização inválida");
  return value.split(".").map(Number);
}
function newer(next, current) {
  const a = versionNumber(next),
    b = versionNumber(current);
  for (let i = 0; i < 3; i++) {
    if (a[i] > b[i]) return true;
    if (a[i] < b[i]) return false;
  }
  return false;
}
async function hashFile(file) {
  const hash = crypto.createHash("sha256");
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest("hex");
}
async function verifyUpdate({
  installerPath,
  manifest,
  publicKey,
  currentVersion,
}) {
  if (
    !manifest ||
    Object.keys(manifest).sort().join(",") !== "payload,signature"
  )
    throw new Error("Manifesto inválido");
  const p = manifest.payload;
  if (
    !p ||
    Object.keys(p).sort().join(",") !== "file,sha256,size,version" ||
    typeof manifest.signature !== "string" ||
    manifest.signature.length > 200
  )
    throw new Error("Formato de assinatura inválido");
  if (
    !crypto.verify(
      null,
      Buffer.from(JSON.stringify(p)),
      publicKey,
      Buffer.from(manifest.signature, "base64"),
    )
  )
    throw new Error(
      "Assinatura da atualização não corresponde à chave confiável da ALT-AI",
    );
  if (!newer(p.version, currentVersion))
    throw new Error(
      "Atualização recusada: versão igual ou anterior à instalada",
    );
  if (
    typeof p.file !== "string" ||
    path.basename(installerPath) !== p.file ||
    path.extname(installerPath).toLowerCase() !== ".exe" ||
    !/^[a-f0-9]{64}$/.test(p.sha256) ||
    !Number.isSafeInteger(p.size) ||
    p.size <= 0 ||
    p.size > 2 * 1024 ** 3
  )
    throw new Error("Metadados do instalador inválidos");
  const stat = fs.lstatSync(installerPath);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== p.size)
    throw new Error(
      "Arquivo ou tamanho do instalador não corresponde ao manifesto",
    );
  const digest = await hashFile(installerPath);
  if (digest !== p.sha256)
    throw new Error("O conteúdo do instalador foi alterado");
  return { version: p.version, file: p.file, sha256: digest, size: p.size };
}
module.exports = { verifyUpdate, hashFile, newer };
