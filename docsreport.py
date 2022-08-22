""" Generates a Markdown-formatted report of the GitHub issues for a given repository and, optionally, a given label.

By default, the previous seven (7) days are reported. You can optionally specify --start-date and --end-date to
report on a specific range.

Example - issues with specified label:
    python3 docsreport.py --repo "MicrosoftDocs/azure-docs" --label "develop/subsvc"

Example - full repo:
    python3 docsreport.py --repo "microsoftgraph/microsoft-graph-docs" --all-issues

Example - specific date range (instead of the default 7 days)
    python3 docsreport.py --repo "MicrosoftDocs/azure-docs" --label "develop/subsvc" --start-date 2020-01-01 --end-date 2020-01-31
    python3 docsreport.py --repo "microsoftgraph/microsoft-graph-docs" --all-issues --start-date 2020-01-01 --end-date 2020-01-31
"""

import argparse
import os
import os.path
from collections import OrderedDict
from datetime import datetime, timedelta
from github import Github
from aliases import gh_to_msft_aliases
from aliases import identity_pm_gh_aliases

GH_ACCESS_TOKEN = os.getenv('GH_ACCESS_TOKEN')

# Use HTML for the flair images since copy/paste of Markdown-style images (:warning:) into email doesn't
# render the images once pasted in.
FLAIR_SIZE = "16"
DAY_30_FLAIR = f'<img src="https://github.githubassets.com/images/icons/emoji/unicode/26a0.png" width="{FLAIR_SIZE}" height="{FLAIR_SIZE}" />'
DAY_90_FLAIR = f'<img src="https://github.githubassets.com/images/icons/emoji/unicode/2622.png" width="{FLAIR_SIZE}" height="{FLAIR_SIZE}" />'
QUESTION_FLAIR = f'<img src="https://github.githubassets.com/images/icons/emoji/unicode/2753.png" width="{FLAIR_SIZE}" height="{FLAIR_SIZE}" />'
TIP_FLAIR = f'<img src="https://github.githubassets.com/images/icons/emoji/unicode/2139.png" width="{FLAIR_SIZE}" height="{FLAIR_SIZE}" />'
FLAIR_LEGEND = (f'{DAY_30_FLAIR} = older than 30 days <br/>\n'
                f'{DAY_90_FLAIR} = older than 90 days')

HEADER = []  # Doc header (H1) and repo details
TOC_PM = []  # List of PM assignees hyperlinked to their sections in the body
TOC = []     # List of assignees hyperlinked to their sections in the body
BODY_PM = [] # H3s and issue tables for each PM assignee
BODY = []    # H3s and issue tables for each assignee (and Unassigned)
ISSUE_TABLE_HEADER = ('| Issue | Days open | Assignee | Opened | Title |\n'
                      '| :---: | :-------: | -------- | ------ | ----- |')

# Defines whether the comment automation tip is added
# Only the following repos support hashtag command automation (e.g. #reassign and #please-close)
AUTOMATION_SUPPORTED_REPOS = ['MicrosoftDocs/azure-docs']


def parse_args():
    """Parse input from the command line.

    Returns:
        args -- ArgumentParser object
    """
    parser = argparse.ArgumentParser(description='Generates a Markdown-formatted report with tables for each assignee of the issues in the specified repo and with the specified label.')
    parser.add_argument('--repo', default='MicrosoftDocs/azure-docs', type=str, help='The repository name in Organization/Repository format.')
    parser.add_argument('--label', default='develop/subsvc', type=str, help='The label applied to the issues you want to pull.')
    parser.add_argument('--saas', default='saas-apps/subsvc', type=str, help='The label test applied to the issues you want to pull.')
    parser.add_argument('--all-issues', action='store_true', help='Generate a report for all open issues in the specified repository, assigned or not. If --all-issues is specified, the --label value is ignored.')
    parser.add_argument('--display-pm-section', action='store_true', help='Display issues assigned to Identity division team members in a separate report section under its own H2 heading.')
    parser.add_argument('--start-date', type=datetime.fromisoformat, help='Report issues from this date (in YYYY-MM-DD format). You must specify --end-date if you pass this arg.')
    parser.add_argument('--end-date', type=datetime.fromisoformat, help='Report issues through this date (in YYYY-MM-DD format). You must specify --start-date if you pass this arg.')
    args = parser.parse_args()
    return args


def get_assignee(issue):
    """Returns the GitHub alias of the specified issue's assignee

    Arguments:
        issue {GitHub.Issue} -- GitHub issue as obtained via GitHub.search_issues() or Repository.get_issues()

    Returns:
        str -- GitHub alias of issue assignee (lowercase)
    """
    return issue.assignee.login.lower()


def get_issue_row(issue, pm_assignee=None):
    """Gets a Markdown table row with several columns containing several of the issue's property values.

    Arguments:
        issue {GitHub.Issue} -- GitHub issue as obtained via GitHub.search_issues() or Repository.get_issues()

    Returns:
        str -- A Markdown row containing details for the issue.
    """
    # If issue was opened less than 24 hours ago, set the age to 0 (otherwise it's -1)
    age = (1 if (datetime.now() - issue.created_at).days < 0 else (datetime.now() - issue.created_at).days)
    # Set appropriate flair for issues over N days old
    if age >= 90:
        flair = DAY_90_FLAIR
    elif age >= 30:
        flair = DAY_30_FLAIR
    else:
        flair = ""

    assignee = 'None' if issue.assignee is None else issue.assignee.login

    # Print the issue details row.
    return f'| [{issue.number}]({issue.html_url}) | {age} {flair} | {assignee} | {issue.created_at.strftime("%Y-%m-%d")} | {issue.title} |'


def get_issue_stats(github, issue_action="closed", from_date=(datetime.now() - timedelta(days=7)), to_date=datetime.now()):
    """Gets a count of issues that were applied the specified action (e.g. 'closed' or 'created') within the specified
    date range. Default is issues within the last 7 days.

    Typically used to get a count of all issues that were open or closed within the last week.

    Arguments:
        github {GitHub} -- GitHub object.
        issue_action {str} -- The action applied to the issue, for example 'closed' or 'created'.
        from_date {datetime} -- Get issues from this date.
        to_date {datetime} -- Get issues through this date (inclusive).
    Returns:
        int -- A Markdown row containing details for the issue.
    """
    date_start = from_date.strftime("%Y-%m-%d")
    date_end = to_date.strftime("%Y-%m-%d")
    if config.all_issues is True:
        issue_query = f"repo:{config.repo} is:issue {issue_action}:{date_start}..{date_end}"
    else:
        issue_query = f"repo:{config.repo} is:issue label:{config.label} {issue_action}:{date_start}..{date_end}"

    issues = github.search_issues(f"{issue_query}")

    return issues.totalCount


def get_assignee_section(assignee_section, assignee, issue_rows, pm_ms_alias=None):
    """Gets the Markdown section (header and table with issues rows) for the specified assignee.

    Arguments:
        assignee_section {list} -- The section
        assignee {string} -- The GitHub alias of the assignee.
        issue_rows {list} -- A list of Markdown table issue detail rows obtained via get_issue_row().
    """
    if pm_ms_alias:
        assignee_section.append(f'### {assignee} - @{pm_ms_alias}' + '\n')
    assignee_section.append(f'### {assignee}' + '\n')
    assignee_section.append('\n')
    assignee_section.append(ISSUE_TABLE_HEADER + '\n')
    assignee_section.append('\n'.join(issue_rows))

    return assignee_section


def save_recipients_to_file(recipient_aliases, recipient_section_header=f'## RECIPIENTS {datetime.now().strftime("%Y-%m-%d")}', recipient_file='recipients.txt', overwrite_contents=False):
    """Generates or appends to a file containing the @microsoft.com aliases of the specified aliases.

    Default behavior is to APPEND to the recipients file. To OVERWRITE an existing recipients file, specify overwrite_contents=false.

    Example format contents:

    ### app-mgmt/subsvc
    alias1@microsoft.com;
    alias2@microsoft.com;
    """

    recipient_addresses = list(dict.fromkeys([alias + '@microsoft.com;' for alias in recipient_aliases]))

    file_contents = recipient_section_header + '\n' + '\n'.join(recipient_addresses) + '\n\n'

    write_mode = "w" if overwrite_contents else "a"

    with open(recipient_file, write_mode) as recipient_out_file:
        recipient_out_file.write(file_contents)


def create_issue_report(config):
    """Produces the report output in Markdown format and sends it to STDOUT.

    Each section of the report is an H3 (###) with assignee's GitHub alias, followed by
    a table of the issues assigned to them. Unassigned issues, if any, are printed last.

    Arguments:
        config {ArgumentParser} -- Arguments containing the repo, label, and any other required or optional settings.
    """
    g = Github(GH_ACCESS_TOKEN)
    r = g.get_repo(config.repo)
    report_start_date = from_date=(datetime.now() - timedelta(days=7))   # default is last 7 days
    report_end_date = to_date=datetime.now()
    assigned_issue_count = 0 # TOTAL assigned issues
    unassigned_issue_count = 0
    pm_assignee_issue_count = 0 # Always 0 unless --display-pm-issue-section
    other_assignee_issue_count = 0
    msft_aliases = []

    # Get the stats for number of opened and closed issues

    # If the start/end dates were specified on the cmd line, use those
    if config.start_date is not None:
        report_start_date = config.start_date
        report_end_date = config.end_date

    closed_count = get_issue_stats(g, "closed", report_start_date, report_end_date)
    opened_count = get_issue_stats(g, "created", report_start_date, report_end_date)

    # Pull the issues from the repo. Since get_issues() pulls both issues and PRs, we have to
    # filter out the PRs later. Ideally, we'd instead use search_issues() on the GitHub object,
    # but that limits to 1000 results so we use this. This way is MUCH slower.
    if config.all_issues is True:
        assigned_issues = r.get_issues(state='open',sort='created-desc',assignee='*')
        unassigned_issues = r.get_issues(state='open',sort='created-desc',assignee='none')
    else:
        assigned_issues = r.get_issues(state='open',sort='created-desc',assignee='*',labels=[config.label])
        unassigned_issues = r.get_issues(state='open',sort='created-desc',assignee='none',labels=[config.label])

    repo_link = f'[{config.repo}](https://github.com/{config.repo})'

    assignee_section = []

    if config.display_pm_section is True:
        TOC_PM.append('- [**Identity team assignees**](#identity-team-assignees) (COUNT issues) ')
        BODY_PM.append('\n## Identity team assignees')
        TOC.append('- [**All other assignees**](#all-other-assignees) (COUNT issues) ')
        BODY.append('\n## All other assignees')
    else:
        TOC.append('- **Assigned issues** (COUNT)')

    # Assemble the sections for each assignee and their table of issues
    sorted_assigned_issues = sorted(assigned_issues, key=get_assignee)
    current_assignee = '' 
    issue_rows = []
    for issue in sorted_assigned_issues:
        # Only process the issue if it's NOT a PR
        if issue.pull_request is None:
            if current_assignee != issue.assignee.login:
                if len(issue_rows) > 0:
                    if config.display_pm_section is True and current_assignee in identity_pm_gh_aliases:
                        TOC_PM.append(f'  - [{current_assignee}](#{current_assignee.lower()}) ({len(issue_rows)})')
                        BODY_PM.append('')

                        pm_ms_alias = ""

                        if current_assignee in gh_to_msft_aliases:
                            pm_ms_alias = gh_to_msft_aliases[current_assignee]

                        BODY_PM.append(''.join(get_assignee_section(assignee_section, current_assignee, issue_rows)))
                        pm_assignee_issue_count += len(issue_rows)
                    else:
                        TOC.append(f'  - [{current_assignee}](#{current_assignee.lower()}) ({len(issue_rows)})')
                        BODY.append('')
                        BODY.append(''.join(get_assignee_section(assignee_section, current_assignee, issue_rows)))
                        other_assignee_issue_count += len(issue_rows)

                    assigned_issue_count += len(issue_rows)
                    issue_rows.clear()
                    assignee_section.clear()
                current_assignee = issue.assignee.login
                if current_assignee in gh_to_msft_aliases:
                    msft_aliases.append(gh_to_msft_aliases[current_assignee])
                else:
                    msft_aliases.append(f'[==-== {current_assignee} ==-==]') # MSFT ALIAS NOT FOUND

            # Add the issue details row
            issue_rows.append(get_issue_row(issue))

    # Catch the last assignee
    # TODO: Repeated code alert! This should be in a function.
    if config.display_pm_section is True and current_assignee in identity_pm_gh_aliases:
        TOC_PM.append(f'  - [{current_assignee}](#{current_assignee.lower()}) ({len(issue_rows)})')
        BODY_PM.append('')
        BODY_PM.append(''.join(get_assignee_section(assignee_section, current_assignee, issue_rows)))
        pm_assignee_issue_count += len(issue_rows)
    else:
        TOC.append(f'  - [{current_assignee}](#{current_assignee.lower()}) ({len(issue_rows)})')
        BODY.append('')
        BODY.append(''.join(get_assignee_section(assignee_section, current_assignee, issue_rows)))
        other_assignee_issue_count += len(issue_rows)
    assigned_issue_count += len(issue_rows)
    if current_assignee in gh_to_msft_aliases:
        msft_aliases.append(gh_to_msft_aliases[current_assignee])
    else:
        # ALIAS NOT FOUND in aliases.py
        # Use https://repos.opensource.microsoft.com/people and then add the alias to aliases.py
        msft_aliases.append(f'[==-== {current_assignee} ==-==]') # MSFT ALIAS NOT FOUND

    if unassigned_issues.totalCount > 0:

        # Print the header for unassigned issues
        BODY.append('')
        BODY.append(f'### Unassigned')
        BODY.append('')
        BODY.append(ISSUE_TABLE_HEADER)

        # Assemble the UNASSIGNED issue details
        for issue in unassigned_issues:
            if issue.pull_request is None:
                # Print the issue details row
                BODY.append(get_issue_row(issue))
                unassigned_issue_count += 1

        if unassigned_issue_count > 0:
            TOC.append(f'- [**Unassigned**](#unassigned) ({str(unassigned_issue_count)})')

    # Now that we have to counts of assigned & unassigned issues **NOT** including PRs, we can
    # assemble the doc header (H1) and the repo + issue count info
    issue_total = assigned_issue_count + unassigned_issue_count
    label = '' if config.all_issues is True else f'<br/> Label: `{config.label}`'
    closed_column_header = f'Closed <br/>{report_start_date.strftime("%Y-%m-%d")} <br /> to <br /> {report_end_date.strftime("%Y-%m-%d")}'
    opened_column_header = f'Opened <br/>{report_start_date.strftime("%Y-%m-%d")} <br /> to <br /> {report_end_date.strftime("%Y-%m-%d")}'
    HEADER.append(FLAIR_LEGEND)
    HEADER.append('')
    HEADER.append(f'## GitHub issues {datetime.now().strftime("%Y-%m-%d")}')
    HEADER.append('')
    HEADER.append(f'| Repository   | Assigned | Unassigned | TOTAL <br/>OPEN | {closed_column_header} | {opened_column_header} |')
    HEADER.append('| :----------: | :------: | :--------: | :---: | :---: | :---: |')
    HEADER.append(f'| {repo_link}{label} | {assigned_issue_count} | {unassigned_issue_count} | **{issue_total}** | {closed_count} | {opened_count} |')
    HEADER.append('')
    if config.repo in AUTOMATION_SUPPORTED_REPOS:
        HEADER.append(f'> {TIP_FLAIR} TIP: You can **reassign** (`#reassign:<GitHubID>`) and **close** (`#please-close`) issues by using hashtag comments - see [Hashtag commands for managing issues with Read permissions](https://review.docs.microsoft.com/help/onboard/github-issues-automation?branch=main#hashtag-commands-for-managing-issues-with-read-permissions)')
        HEADER.append('')
    elif 'microsoftgraph/microsoft-graph-docs' in config.repo:
        HEADER.append(f'> {QUESTION_FLAIR} Questions or feedback? Contact [MSGraphDocsVteam@microsoft.com](mailto:MSGraphDocsVteam@microsoft.com)')
        HEADER.append('')

    if config.display_pm_section is True:
        TOC_PM[0] = TOC_PM[0].replace('COUNT', str(pm_assignee_issue_count))
        TOC[0] = TOC[0].replace('COUNT', str(other_assignee_issue_count))
        print('\n'.join(HEADER + TOC_PM + TOC + BODY_PM + BODY).encode(encoding="ascii",errors="replace").decode(encoding="ascii",errors="replace"))
    else:
        TOC[0] = TOC[0].replace('COUNT', str(assigned_issue_count))
        print('\n'.join(HEADER + TOC + BODY).encode(encoding="ascii",errors="replace").decode(encoding="ascii",errors="replace"))

    print()

    # Save the MSFT aliases to a file for the To: line in the email reports
    if config.all_issues is True:
        recipient_section_header = f'####################### {config.repo}'
    else:
        recipient_section_header = f'####################### {config.repo} | {config.label}'
    recipient_file_timestamp = datetime.now().strftime("%Y-%m-%d")
    recipient_address_file = os.path.join(os.curdir, 'recipients-' + recipient_file_timestamp + '.txt')
    save_recipients_to_file(msft_aliases, recipient_section_header, recipient_address_file, False)

    # MAIN END - job is done!

if __name__ == '__main__':
    config = parse_args()
    create_issue_report(config)
