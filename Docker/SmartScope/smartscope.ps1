# Define constants
$cmd_file = "dockerCmd.txt"
$dockerRepo = "ghcr.io/niehs/smartscope"
$composeCmd = "docker compose"
$dockerCmd = "docker"

# Check if the command file exists and read commands
if (Test-Path $cmd_file) {
    $cmds = Get-Content $cmd_file
    $dockerCmd = $cmds[0]
    $composeCmd = $cmds[1]
}

# Define the help text function
function Show-Help {
    $OPTIONS = @"
Usage: $($MyInvocation.MyCommand.Name) subcommand [command]

Subcommand              DESCRIPTION
==========              ===========
start                   Start SmartScope
stop                    Stop SmartScope
restart                 Restart SmartScope
setup                   Setup the SmartScope directories
update [version]        Update SmartScope to the specified version. Choices: ['latest','stable'] (default: latest)
run [command]           Run a SmartScope command in the SmartScope container
exec [command]          Run any shell command in the SmartScope container
python                  Runs an interactive ipython shell inside the SmartScope container
"@
    Write-Output $OPTIONS
}

# Define the stop function
function Stop-SmartScope {
    Write-Output "Stopping SmartScope"
    & $composeCmd down
}

# Define the start function
function Start-SmartScope {
    $env:UID = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $env:GID = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    Write-Output "Starting SmartScope"
    & $composeCmd -f docker-compose.yml -f smartscope.yml up -d
}

# Define the prompt function
function Prompt-YesNo ($question) {
    while ($true) {
        Write-Output "$question (y/n)"
        $user_input = Read-Host

        if ($user_input -eq "y") {
            return $true
        } elseif ($user_input -eq "n") {
            return $false
        } else {
            Write-Output "Invalid choice. Please enter 'yes' or 'no'."
        }
    }    
}

# Define the check for updates function
function Check-ForUpdates ($version) {
    Write-Output "Checking for updates to version $version"
    $online_sha = & $dockerCmd manifest inspect $dockerRepo:$version | Select-String -Pattern '"digest": "sha256:([^"]*)"' | ForEach-Object { $_.Matches.Groups[1].Value }
    $local_sha = & $dockerCmd inspect --format "{{.ID}}" $dockerRepo:$version | ForEach-Object { $_.Split(':')[1] }
    Write-Output "Online sha: $online_sha`nLocal sha: $local_sha"
    if ($online_sha -eq $local_sha) {
        return $false
    } else {
        return $true
    }
}

# Process the argument
$argument = if ($args.Count -gt 0) { $args[0] } else { Show-Help; exit 1 }

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

switch ($argument) {
    "start" {
        if (Check-ForUpdates 'latest') {
            Write-Output "A new release is available. Run 'smartscope.ps1 update latest' to update to the latest version."
        }
        if (Check-ForUpdates 'stable') {
            Write-Output "A new beta version is available. Run 'smartscope.ps1 update stable' to update to the new beta version."
        }
        Start-SmartScope
    }
    "stop" {
        Stop-SmartScope
    }
    "restart" {
        Stop-SmartScope
        Start-Sleep -Seconds 2
        Start-SmartScope
    }
    "run" {
        $cmd = "$composeCmd exec smartscope smartscope.py $($args[1..$args.Length - 1] -join ' ')"
        Write-Output "Executing command inside the SmartScope container:`n$cmd"
        iex $cmd
    }
    "help" { Show-Help }
    "-h" { Show-Help }
    "--help" { Show-Help }
    "python" {
        Write-Output "Running a python shell inside the SmartScope container"
        & $composeCmd exec -it smartscope manage.py shell -i ipython
    }
    "exec" {
        Write-Output "Executing shell command inside the SmartScope container:"
        & $composeCmd exec -it smartscope $args[1..$args.Length - 1]
    }
    "setup" {
        $version = if ($args.Count -gt 1) { $args[1] } else { 'latest' }
        Write-Output "Setting up the latest version of SmartScope"
        if ($version -eq 'latest') { $version = 'main' }
        Write-Output "Setting up the SmartScope directories"
        New-Item -ItemType Directory -Force -Path logs, shared/nginx, shared/auth, shared/smartscope, db, data, backups
        foreach ($file in @("docker-compose.yml", "smartscope.yml", "smartscope.conf", "database.conf")) {
            Write-Output "Pulling $file from $version"
            if (Test-Path $file) {
                Write-Output "$file already exists. Skipping."
                continue
            }
            Invoke-WebRequest -Uri "https://raw.githubusercontent.com/NIEHS/SmartScope/$version/Docker/SmartScope/$file" -OutFile $file
        }
        Write-Output "Pulling initialdb.sql from $version"
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/NIEHS/SmartScope/$version/Docker/SmartScope/shared/initialdb.sql" -OutFile "shared/initialdb.sql"
    }
    "update" {
        $version = if ($args.Count -gt 1) { $args[1] } else { 'latest' }
        Write-Output "Updating SmartScope to version: $version"
        if (-not (Check-ForUpdates $version)) {
            if (-not (Prompt-YesNo "You already have the docker image corresponding to version $version. Do you want to update this instance anyway?")) {
                exit 0
            }
        }

        $backupDir = "backups/$(Get-Date -Format 'yyyyMMdd')_config_pre_update"
        if (Prompt-YesNo "Do you want to back up the database? (Highly recommended)") {
            Write-Output "Backing up the database. This may take a few minutes."
            & $composeCmd exec smartscope smartscope.py backup_db
        }
        Write-Output "Creating a backup of the configuration in $backupDir"
        New-Item -ItemType Directory -Force -Path $backupDir
        Copy-Item -Path docker-compose.yml, smartscope.yml, smartscope.conf, database.conf, smartscope.ps1 -Destination $backupDir
        Write-Output "Pulling updated docker-compose.yml"
        $repo_url = "https://raw.githubusercontent.com/NIEHS/SmartScope/$version/Docker/SmartScope"
        Invoke-WebRequest -Uri "$repo_url/docker-compose.yml" -OutFile "docker-compose.yml"
        Write-Output "Pulling docker image"
        & $composeCmd pull smartscope
        if (Prompt-YesNo "Files updated, do you want to restart SmartScope") {
            & $MyInvocation.MyCommand.Path restart
        }
    }
    default {
        Write-Output "Unknown command error: $argument"
        Show-Help
        exit 1
    }
}
