param(
  [ValidateSet("loop", "state", "playpause", "next", "prev")]
  [string]$Action = "state"
)

$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

try {
  [void][Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
  [void][Windows.Foundation.IAsyncOperation`1,Windows.Foundation,ContentType=WindowsRuntime]
  [void][Windows.Storage.Streams.IRandomAccessStreamWithContentType,Windows.Storage.Streams,ContentType=WindowsRuntime]
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
} catch {
  '{"ok":false,"error":"winrt"}'
  exit 0
}

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($op, $type, $timeoutMs = 5000) {
  if ($null -eq $op) { return $null }
  $asTask = $asTaskGeneric.MakeGenericMethod($type)
  $task = $asTask.Invoke($null, @($op))
  if (-not $task.Wait($timeoutMs)) { return $null }
  return $task.Result
}

function Get-Manager {
  $type = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
  return Await ($type::RequestAsync()) $type
}

function Get-Session($manager) {
  if ($null -eq $manager) { return $null }
  $sessions = @($manager.GetSessions())
  $cider = $sessions | Where-Object {
    $_.SourceAppUserModelId -match 'Cider'
  } | Select-Object -First 1
  if ($cider) { return $cider }
  $current = $manager.GetCurrentSession()
  if ($current) { return $current }
  foreach ($s in $sessions) {
    $status = $s.GetPlaybackInfo().PlaybackStatus
    if ($status.value__ -eq 4 -or $status.value__ -eq 5) { return $s }
  }
  return $null
}

function Get-Art($props) {
  try {
    if ($null -eq $props.Thumbnail) { return $null }
    $type = [Windows.Storage.Streams.IRandomAccessStreamWithContentType,Windows.Storage.Streams,ContentType=WindowsRuntime]
    $stream = Await ($props.Thumbnail.OpenReadAsync()) $type 3000
    if ($null -eq $stream) { return $null }
    if ($stream.Size -le 0 -or $stream.Size -gt 5000000) { return $null }
    $net = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
    $ms = New-Object System.IO.MemoryStream
    $net.CopyTo($ms)
    $bytes = $ms.ToArray()
    $ms.Dispose()
    $net.Dispose()
    $stream.Dispose()
    if ($bytes.Length -eq 0) { return $null }
    return [Convert]::ToBase64String($bytes)
  } catch {
    return $null
  }
}

function Get-Info($session, [bool]$withArt) {
  if ($null -eq $session) { return [ordered]@{ ok = $false } }
  try {
    $props = Await ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
    $play = $session.GetPlaybackInfo()
    $timeline = $session.GetTimelineProperties()
    $status = $play.PlaybackStatus
    $playing = ($status.value__ -eq 4)
    $position = 0.0
    $duration = 0.0
    if ($null -ne $timeline) {
      $position = [double]$timeline.Position.TotalSeconds
      $duration = [double]($timeline.EndTime.TotalSeconds - $timeline.StartTime.TotalSeconds)
    }
    $title = if ($null -ne $props.Title) { [string]$props.Title } else { "" }
    $artist = if ($null -ne $props.Artist) { [string]$props.Artist } else { "" }
    $album = if ($null -ne $props.AlbumTitle) { [string]$props.AlbumTitle } else { "" }
    $source = [string]$session.SourceAppUserModelId
    $art = $null
    if ($withArt) { $art = Get-Art $props }
    return [ordered]@{
      ok = $true
      key = "$title|$artist|$album"
      title = $title
      artist = $artist
      album = $album
      source = $source
      status = [string]$status
      playing = $playing
      position = [math]::Round($position, 2)
      duration = [math]::Round($duration, 2)
      art = $art
    }
  } catch {
    return [ordered]@{ ok = $false }
  }
}

$manager = Get-Manager
$session = Get-Session $manager

if ($Action -eq "playpause" -or $Action -eq "next" -or $Action -eq "prev") {
  if ($null -eq $session) {
    '{"ok":false,"error":"no session"}'
    exit 0
  }
  $op = $null
  if ($Action -eq "playpause") { $op = $session.TryTogglePlayPauseAsync() }
  elseif ($Action -eq "next") { $op = $session.TrySkipNextAsync() }
  else { $op = $session.TrySkipPreviousAsync() }
  $result = Await $op ([bool])
  if ($result) { '{"ok":true}' } else { '{"ok":false}' }
  exit 0
}

if ($Action -eq "state") {
  $info = Get-Info $session $true
  $info | ConvertTo-Json -Compress
  exit 0
}

$lastKey = ""
$haveArt = $false
while ($true) {
  $manager = Get-Manager
  $session = Get-Session $manager
  if ($null -eq $session) {
    '{"ok":false}'
    $lastKey = ""
    $haveArt = $false
  } else {
    $info = Get-Info $session $false
    if ($info.ok) {
      if ($info.key -ne $lastKey) {
        $lastKey = $info.key
        $haveArt = $false
      }
      if (-not $haveArt) {
        $props = Await ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
        $info.art = Get-Art $props
        $haveArt = $true
      } else {
        $info.art = $null
      }
      $info | ConvertTo-Json -Compress
    } else {
      '{"ok":false}'
    }
  }
  [Console]::Out.Flush()
  Start-Sleep -Milliseconds 1000
}
