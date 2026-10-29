// electron-builder 26.18's NSIS uninstaller step passes only __COMPAT_LAYER
// to execFile on Windows, losing SystemRoot/PATH and causing spawn UNKNOWN.
// Preserve the build environment; keep the normal NSIS/signing pipeline intact.
const { WineVmManager } = require('app-builder-lib/out/vm/WineVm');
const { build, Platform, Arch } = require('electron-builder');
if (process.platform !== 'win32') throw new Error('Build Windows requires Windows.');
const original = WineVmManager.prototype.execWine;
WineVmManager.prototype.execWine = function (input) {
  return original.call(this, {
    ...input,
    options: { ...input.options, env: { ...process.env, ...input.options?.env } },
  });
};
const target = process.argv.includes('--dir') ? 'dir' : 'nsis';
const config = process.argv.includes('--signed')
  ? require('../electron-builder.signed.cjs')
  : require('../package.json').build;
build({ targets: Platform.WINDOWS.createTarget(target, Arch.x64), config, publish: 'never' })
  .catch((error) => { console.error(error); process.exitCode = 1; });
