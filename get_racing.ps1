<#
  Fetches today's horse racing results from Sporting Life and saves them as
  racing_results.js beside ceefax_news.html, where pages 400+ read them.

    get_racing.ps1             fetch once
    get_racing.ps1 -Every 10   keep fetching every 10 minutes (Ctrl+C to stop)

  get_racing.cmd runs the second form, so it can simply be double-clicked.
#>
param([int]$Every = 0)

$ErrorActionPreference = 'Stop'
$out = Join-Path $PSScriptRoot 'racing_results.js'
$url = 'https://www.sportinglife.com/racing/results'
$ua  = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'

function Save-Results {
  $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 -UserAgent $ua $url
  # Decode as UTF-8 ourselves so accented horse names survive
  $html = [Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray())
  $m = [regex]::Match($html, '(?s)<script id="__NEXT_DATA__"[^>]*>(.*?)</script>')
  if (-not $m.Success) { throw 'Results data not found on the page (the site layout may have changed)' }
  $data = $m.Groups[1].Value | ConvertFrom-Json

  $meetings = @(foreach ($mt in $data.props.pageProps.meetings) {
    $ms = $mt.meeting_summary
    [ordered]@{
      course    = $ms.course.name
      country   = $ms.course.country.long_name
      date      = $ms.date
      going     = $ms.going
      abandoned = [bool]$ms.abandoned
      races     = @(foreach ($rc in $mt.races) {
        [ordered]@{
          time    = $rc.time
          name    = $rc.name
          dist    = $rc.distance
          runners = $rc.ride_count
          stage   = $rc.race_stage
          placed  = @(foreach ($h in $rc.top_horses) {
            [ordered]@{ pos = $h.position; name = $h.name; odds = $h.odds; fav = [bool]$h.favourite }
          })
        }
      })
    }
  })
  if (-not $meetings.Count) { throw 'No meetings listed today' }

  $obj = [ordered]@{
    source   = 'Sporting Life'
    # Include the UTC offset: on GitHub's servers local time is UTC, not UK time
    fetched  = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
    date     = $meetings[0].date
    meetings = $meetings
  }
  $json = $obj | ConvertTo-Json -Depth 8 -Compress
  [IO.File]::WriteAllText($out, "window.RACING = $json;`n", (New-Object Text.UTF8Encoding $false))

  $done = @($meetings | ForEach-Object { $_.races } | Where-Object { $_.placed.Count }).Count
  $all  = @($meetings | ForEach-Object { $_.races }).Count
  Write-Host ('{0:HH:mm}  {1} meetings, {2} of {3} races with results -> {4}' -f (Get-Date), $meetings.Count, $done, $all, $out)
}

while ($true) {
  try { Save-Results }
  catch {
    Write-Warning ('{0:HH:mm}  Could not fetch results: {1}' -f (Get-Date), $_.Exception.Message)
    if ($Every -le 0) { exit 1 }
  }
  if ($Every -le 0) { break }
  Start-Sleep -Seconds ($Every * 60)
}
