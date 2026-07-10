# convert_dashboard.ps1
# Converts Grafana v13 API-v2 format JSON to classic "panels: []" format
# for Grafana file-based provisioning (schemaVersion 39).
# Usage: .\convert_dashboard.ps1

$InputFile  = "5G_SMO_Dashboard_Fixed.json"
$OutputFile = "5G_SMO_Dashboard_Provisioned.json"

Write-Host "Reading $InputFile..."
$src = Get-Content $InputFile -Raw | ConvertFrom-Json

# ── Build classic panels array from layout items ───────────────────────────────
$panels = @()

foreach ($item in $src.spec.layout.spec.items) {
    $ref = $item.spec.element.name          # e.g. "panel-3"
    $elem = $src.spec.elements.$ref
    if (-not $elem) { Write-Warning "Element $ref not found, skipping"; continue }

    $ps = $elem.spec

    # Grid position from layout item
    $gridPos = [ordered]@{
        x = [int]$item.spec.x
        y = [int]$item.spec.y
        w = [int]$item.spec.width
        h = [int]$item.spec.height
    }

    # Panel type — in v2 format it's stored in vizConfig.group
    $panelType = if ($ps.vizConfig -and $ps.vizConfig.group) {
        $ps.vizConfig.group
    } else {
        "timeseries"
    }

    # Options and fieldConfig are nested inside vizConfig.spec
    $vizOptions     = if ($ps.vizConfig -and $ps.vizConfig.spec -and $ps.vizConfig.spec.options)     { $ps.vizConfig.spec.options     } else { @{} }
    $vizFieldConfig = if ($ps.vizConfig -and $ps.vizConfig.spec -and $ps.vizConfig.spec.fieldConfig) { $ps.vizConfig.spec.fieldConfig } else { @{ defaults = @{}; overrides = @() } }

    # Build targets array from queries
    $targets = @()
    if ($ps.data -and $ps.data.spec -and $ps.data.spec.queries) {
        foreach ($q in $ps.data.spec.queries) {
            $qs = $q.spec
            $target = [ordered]@{
                refId      = $qs.refId
                hide       = [bool]$qs.hidden
                datasource = [ordered]@{ uid = "bfnbcxajfec5cb"; type = "marcusolsson-json-datasource" }
            }
            # Copy the query-specific spec fields (urlPath, fields, method, etc.)
            if ($qs.query -and $qs.query.spec) {
                $qs.query.spec.PSObject.Properties | ForEach-Object {
                    $target[$_.Name] = $_.Value
                }
            }
            $targets += $target
        }
    }

    # Collect transformations if present
    $transformations = @()
    if ($ps.data -and $ps.data.spec -and $ps.data.spec.transformations) {
        $transformations = $ps.data.spec.transformations
    }

    # Assemble the classic panel object
    $panel = [ordered]@{
        id              = [int]$ps.id
        title           = $ps.title
        type            = $panelType
        gridPos         = $gridPos
        datasource      = [ordered]@{ uid = "bfnbcxajfec5cb"; type = "marcusolsson-json-datasource" }
        targets         = $targets
        transformations = $transformations
        options         = $vizOptions
        fieldConfig     = $vizFieldConfig
        description     = if ($ps.description) { $ps.description } else { "" }
    }

    $panels += $panel
}

# ── Time settings ───────────────────────────────────────────────────────────────
$ts   = $src.spec.timeSettings
$from = if ($ts -and $ts.from) { $ts.from } else { "now-1h" }
$to   = if ($ts -and $ts.to)   { $ts.to }   else { "now" }
$tz   = if ($ts -and $ts.timezone) { $ts.timezone } else { "browser" }
$ref  = if ($ts -and $ts.autoRefresh) { $ts.autoRefresh } else { "5s" }

# ── Assemble classic root ────────────────────────────────────────────────────────
$classic = [ordered]@{
    id            = $null
    uid           = $src.metadata.uid
    title         = $src.spec.title
    tags          = $src.spec.tags
    timezone      = $tz
    schemaVersion = 39
    version       = [int]$src.metadata.generation
    refresh       = $ref
    time          = [ordered]@{ from = $from; to = $to }
    panels        = $panels
}

Write-Host "Writing $OutputFile with $($panels.Count) panels..."
$classic | ConvertTo-Json -Depth 30 | Set-Content $OutputFile -Encoding UTF8
Write-Host ""
Write-Host "All panels converted:"
$panels | ForEach-Object { Write-Host "  id=$($_.id.ToString().PadLeft(2))  type=$($_.type.PadRight(12))  title='$($_.title)'" }
Write-Host ""
Write-Host "Done. Use $OutputFile for Grafana provisioning."
