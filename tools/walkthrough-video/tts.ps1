Add-Type -AssemblyName System.Speech
$scenes = Get-Content -Raw -Path "C:\dev\video\scenes.json" | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice("Microsoft Zira Desktop")
$s.Rate = 0
foreach ($sc in $scenes) {
  $out = "C:\dev\video\audio\$($sc.id).wav"
  $s.SetOutputToWaveFile($out)
  $s.Speak($sc.text)
}
$s.SetOutputToNull()
$s.Dispose()
