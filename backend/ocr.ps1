# Fixed local OCR helper. Input is JSON on stdin, never executable commands.
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$altAsTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
function Await-AltOperation($operation, $resultType) {
    $task = $altAsTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
}
$altInput = [Console]::In.ReadToEnd() | ConvertFrom-Json
$altEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('pt-BR'))
if ($null -eq $altEngine) { $altEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if ($null -eq $altEngine) { throw 'OCR local indisponivel: instale um idioma de reconhecimento do Windows.' }
$altResults = @()
foreach ($altImagePath in $altInput.paths) {
    $altStream = $null
    $altBitmap = $null
    try {
        $altFile = Await-AltOperation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($altImagePath)) ([Windows.Storage.StorageFile])
        $altStream = Await-AltOperation ($altFile.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
        $altDecoder = Await-AltOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($altStream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $altBitmap = Await-AltOperation ($altDecoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $altResult = Await-AltOperation ($altEngine.RecognizeAsync($altBitmap)) ([Windows.Media.Ocr.OcrResult])
        $altResults += [pscustomobject]@{ text = (($altResult.Lines | ForEach-Object { $_.Text }) -join "`n") }
    } finally {
        if ($null -ne $altBitmap) { $altBitmap.Dispose() }
        if ($null -ne $altStream) { $altStream.Dispose() }
    }
}
ConvertTo-Json -InputObject @($altResults) -Compress -Depth 4
