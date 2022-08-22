# Generate GitHub issue reports in Markdown format

The docsreport.py Python script generates a Markdown-formatted report containing the issues and the their assignees for a given GitHub repository and label.

Issues are grouped by assignee, with those older than 30 and 90 days identified by "caution" and "radioactive" icons, respectively. A header on the report includes a few issue statistics like number of issues open, assigned, unassigned, and closed and opened in last the week.

![Example report rendered in Markdown](./media/output-01.png)

## Prerequisites

* Python 3.7+
* GitHub [personal access token](https://help.github.com/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line)
