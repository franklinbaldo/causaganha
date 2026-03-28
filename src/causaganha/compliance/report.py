from datetime import datetime

from fpdf import FPDF

from causaganha.storage.connection import get_connection


class LGPDComplianceReport(FPDF):
    def __init__(
        self,
        period: str,
        controller: str = "Franklin / CausaGanha",
        basis: str = "Judicial transparency",
    ) -> None:
        super().__init__()
        self.period = period
        self.controller = controller
        self.basis = basis

    def header(self) -> None:
        # Arial bold 15
        self.set_font("Arial", "B", 15)
        # Title
        self.cell(0, 10, "LGPD Compliance Report", 0, 1, "C")
        self.set_font("Arial", "", 12)

        # Meta info
        self.cell(0, 8, f"Period: {self.period}", 0, 1, "L")
        self.cell(0, 8, f"Data Controller: {self.controller}", 0, 1, "L")
        self.cell(0, 8, f"Processing Basis: {self.basis}", 0, 1, "L")

        # Line break
        self.ln(10)

    def chapter_title(self, num: int, label: str) -> None:
        self.set_font("Arial", "B", 12)
        # Background color
        self.set_fill_color(200, 220, 255)
        # Title
        self.cell(0, 10, f"Section {num}: {label}", 0, 1, "L", 1)
        # Line break
        self.ln(4)

    def chapter_body(self, text: str) -> None:
        # Times 12
        self.set_font("Times", "", 12)
        # Output text
        self.multi_cell(0, 10, text)
        # Line break
        self.ln()

    def generate_report(self, filepath: str, access_logs: str) -> None:
        self.add_page()

        # Section 1
        self.chapter_title(1, "Data Access Log")
        self.chapter_body(access_logs)

        # Section 2
        self.chapter_title(2, "Data Retention")
        retention_text = """Hotline: 3 months rolling (fast access)
Cold: 6+ months (Archived to AWS S3 Glacier)
Deletion policy: Automated deletion after 24 months total retention period."""
        self.chapter_body(retention_text)

        # Section 3
        self.chapter_title(3, "Third-party Sharing")
        sharing_text = """BigQuery exports: External Analytics Team A
Webhook deliveries: Legal Tech Partner X (https://partner-x.com/webhook)
Archive locations: AWS S3 Glacier (causaganha-archive/cold)"""
        self.chapter_body(sharing_text)

        # Section 4
        self.chapter_title(4, "Security Measures")
        security_text = """Encryption in transit: TLS 1.3 enabled for all API and dashboard traffic.
Encryption at rest: AWS S3 KMS enabled for cold storage.
Access controls: Authentication required for all dashboard and API access.
Audit logging: Enabled for all data access and administrative actions."""
        self.chapter_body(security_text)

        # Output
        self.output(filepath, "F")


def _get_access_logs(year: int, month: int) -> str:
    con = get_connection()
    try:
        # Construct start and end dates
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

        # Query audit_log table
        query = """
            SELECT user_identifier, action_type, resource_accessed, accessed_at, ip_address
            FROM audit_log
            WHERE accessed_at >= ? AND accessed_at < ?
            ORDER BY accessed_at DESC
            LIMIT 50
        """
        results = con.con.execute(query, [start_date, end_date]).fetchall()

        if not results:
            return "No access logs found for the period."

        formatted_logs = []
        for row in results:
            user, action, resource, accessed_at, ip = row
            # fpdf doesn't like unicode sometimes, so simplify string
            formatted_logs.append(
                f"User: {user} | IP: {ip}\nTime: {accessed_at}\nAction: {action} | Resource: {resource}\n"
            )

        return "\n".join(formatted_logs)

    except Exception as e:
        return f"Failed to retrieve access logs: {e}"


def generate_monthly_report() -> None:
    # Typically, get current month/year for the period
    now = datetime.now()
    period = f"{now.strftime('%B')} {now.year}"

    # Get the logs from duckdb
    access_logs = _get_access_logs(now.year, now.month)

    report = LGPDComplianceReport(period=period)

    # Generate PDF
    pdf_filepath = f"lgpd_report_{now.strftime('%Y_%m')}.pdf"
    report.generate_report(filepath=pdf_filepath, access_logs=access_logs)

    # Generate HTML equivalent
    html_filepath = f"lgpd_report_{now.strftime('%Y_%m')}.html"
    with open(html_filepath, "w") as f:
        # Escape html chars
        html_logs = access_logs.replace("\n", "<br>")

        f.write(f"""
        <html>
        <head><title>LGPD Compliance Report - {period}</title></head>
        <body>
            <h1>LGPD Compliance Report</h1>
            <p><strong>Period:</strong> {period}</p>
            <p><strong>Data Controller:</strong> Franklin / CausaGanha</p>
            <p><strong>Processing Basis:</strong> Judicial transparency</p>

            <h2>Section 1: Data Access Log</h2>
            <p>{html_logs}</p>

            <h2>Section 2: Data Retention</h2>
            <p>Hotline: 3 months rolling (fast access)<br>
            Cold: 6+ months (Archived to AWS S3 Glacier)<br>
            Deletion policy: Automated deletion after 24 months total retention period.</p>

            <h2>Section 3: Third-party Sharing</h2>
            <p>BigQuery exports: External Analytics Team A<br>
            Webhook deliveries: Legal Tech Partner X (https://partner-x.com/webhook)<br>
            Archive locations: AWS S3 Glacier (causaganha-archive/cold)</p>

            <h2>Section 4: Security Measures</h2>
            <p>Encryption in transit: TLS 1.3 enabled for all API and dashboard traffic.<br>
            Encryption at rest: AWS S3 KMS enabled for cold storage.<br>
            Access controls: Authentication required for all dashboard and API access.<br>
            Audit logging: Enabled for all data access and administrative actions.</p>
        </body>
        </html>
        """)


if __name__ == "__main__":
    generate_monthly_report()
