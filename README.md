# Generate GitHub issue reports in Markdown format

The docsreport.py Python script generates a Markdown-formatted report containing the issues and the their assignees for a given GitHub repository and label.

Issues are grouped by assignee, with those older than 30 and 90 days identified by "caution" and "radioactive" icons, respectively. A header on the report includes a few issue statistics like number of issues open, assigned, unassigned, and closed and opened in last the week.

## Prerequisites

- Python 3.7+
- GitHub [personal access token](https://help.github.com/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/henrymbuguakiarie/github-issues-saas-tutorial.git
```

### 2. Configure the script

Open the `runreports.sh` file in your code and modify the following values:

```bash
REPODIR="/home/$USER/repos"
VENV="/home/$USER/venv/docsreport"
PAT="YOUR_GITHUB_PERSONAL_ACCESS_TOKEN_HERE"
```

## Run the application

Execute the following command to get the app up and running

```bash
./runreports.sh
```
