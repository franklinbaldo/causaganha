# Develop Web Dashboard

## Problem Statement
- **What problem does this solve?**
  Currently, monitoring the CausaGanha pipeline, viewing statistics, and managing processing jobs relies on CLI commands and direct database inspection. This can be cumbersome, especially for a quick overview or for users less comfortable with the command line.
- **Why is this important?**
  A web dashboard would provide a user-friendly, accessible interface for monitoring the system's health, tracking progress, viewing key metrics, and potentially performing basic administrative tasks. This enhances usability and transparency.
- **Current limitations**
  - No graphical user interface for monitoring or management.
  - Real-time status updates are not easily visualized.
  - Accessing statistics requires running specific CLI commands.
  - No centralized view of pipeline activity or potential issues.

## Proposed Solution
- **High-level approach**
  Develop a lightweight web dashboard using a simple Python web framework (like FastAPI or Flask) that reads data from the CausaGanha DuckDB database and potentially other status files to display key information. For a first version, focus on read-only monitoring and statistics.
- **Technical architecture**
  1.  **Web Framework**:
      - Choose a lightweight Python web framework:
          - **FastAPI**: Good for building APIs quickly, modern, async support. Could serve a simple HTML frontend or be a backend for a separate JS frontend.
          - **Flask**: Simple, mature, and flexible. Good for server-rendered HTML.
          - **Streamlit/Dash**: Excellent for data-focused dashboards with minimal web development overhead, might be the quickest way to a useful internal tool.
      - For simplicity and rapid development, **Streamlit** or **Flask with server-rendered templates** is recommended for an initial version.
  2.  **Data Source**: The dashboard will primarily read data from the `data/causaganha.duckdb` database. It should use the existing `CausaGanhaDB` class or direct read-only connections.
  3.  **Key Dashboard Sections (Initial Version)**:
      - **Overview/Status**:
          - Total diários in queue by status (queued, archived, analyzed, scored, failed).
          - Recent activity (e.g., diários processed in the last 24 hours).
          - System health indicators (e.g., database connection status, last successful pipeline run).
      - **Job Queue Details**:
          - A paginated, searchable table view of the `job_queue` table with key details (URL, tribunal, date, status, last updated).
          - Ability to filter by status or tribunal.
      - **Statistics**:
          - Visualization of OpenSkill rating distribution.
          - Top N lawyers by rating.
          - Number of decisions processed over time.
          - Processing speed (e.g., diários/hour for different stages).
      - **Configuration View**: Display current settings from `config.toml` (read-only).
  4.  **Deployment (Initial)**:
      - Can be run as a local web server (`uv run python dashboard.py`).
      - Not intended for public internet exposure initially without proper security considerations.
  5.  **Auto-Refresh (Optional)**: Implement basic auto-refresh for dashboard data using meta refresh tags or simple JavaScript.

- **Implementation steps**
  1.  **Phase 1: Framework Selection and Basic Setup (Week 1)**
      - Evaluate and choose the web framework (e.g., Streamlit, Flask, or FastAPI).
      - Set up the basic project structure for the dashboard application (e.g., `dashboard/app.py`).
      - Implement a basic connection to the DuckDB database (read-only).
  2.  **Phase 2: Overview and Statistics Pages (Weeks 2-3)**
      - Develop the "Overview/Status" page, displaying counts from `job_queue` and basic system health.
      - Develop the "Statistics" page, visualizing key metrics from the `ratings` and `partidas` tables. Use simple charts if the framework supports them easily (e.g., Matplotlib with Flask, or built-in Streamlit charts).
  3.  **Phase 3: Job Queue Details Page (Week 4)**
      - Implement the "Job Queue Details" page with a searchable and filterable table of jobs.
  4.  **Phase 4: Styling and Usability (Week 5)**
      - Apply basic styling for readability and usability.
      - Add navigation between dashboard sections.
      - Implement auto-refresh for data if feasible.
  5.  **Phase 5: Documentation and Refinement (Week 6)**
      - Document how to run and use the dashboard.
      - Gather feedback and make minor improvements.
      - Add a section to display current configuration.

## Success Criteria
- **Functional Dashboard**: A web dashboard is available that displays key pipeline statuses and statistics.
- **Read-Only Access**: The dashboard can successfully read and display data from the DuckDB database without modifying it.
- **Key Information Displayed**:
    - Overview of job statuses (queued, archived, analyzed, scored, failed).
    - Basic OpenSkill rating statistics.
    - A view of items in the job queue.
- **Usability**: The dashboard is easy to navigate and understand.
- **Local Deployment**: The dashboard can be run locally by a developer or administrator.
- **No Impact on Core Pipeline**: The dashboard operates as a separate process and does not interfere with the main CausaGanha CLI or async pipeline operations.

## Implementation Plan (High-Level for this document)
1.  **Choose Framework & Setup**: Select Streamlit/Flask/FastAPI. Basic app structure, DB connection.
2.  **Develop Overview & Stats Pages**: Display `job_queue` summaries and `ratings` statistics.
3.  **Develop Job Queue Page**: Implement a table view of the `job_queue`.
4.  **Basic Styling & Navigation**: Improve usability. Add auto-refresh if simple.
5.  **Document & Refine**: Write setup/usage guide. Add config view.

## Risks & Mitigations
- **Risk 1: Scope Creep**: The dashboard could grow into a complex web application.
  - *Mitigation*: Strictly limit the scope for the initial version to read-only monitoring and essential statistics. Define clear boundaries for what the dashboard will and will not do.
- **Risk 2: Performance Impact on Database**: Frequent queries from the dashboard could impact the performance of the main pipeline if it's accessing the same DuckDB file.
  - *Mitigation*:
    - Use read-only database connections.
    - Optimize dashboard queries for efficiency.
    - Implement caching for dashboard data if necessary (though likely overkill for an initial version with DuckDB).
    - Ensure dashboard queries are not excessively frequent.
- **Risk 3: Web Development Complexity**: If a full-fledged framework like FastAPI with a separate frontend is chosen, web development expertise is required.
  - *Mitigation*: For an initial version, prioritize simplicity. Streamlit is designed for rapid dashboard development by Python developers without extensive web frontend experience. Flask with server-side templates is also relatively straightforward.
- **Risk 4: Security**: If the dashboard is ever exposed beyond localhost, security becomes a major concern.
  - *Mitigation*: For the initial version, explicitly state that it's for local use only. If wider access is needed later, it would require a separate plan addressing authentication, authorization, and other web security best practices.
- **Risk 5: Stale Data**: Dashboard data might not be perfectly real-time.
  - *Mitigation*: Implement a reasonable refresh interval. Clearly indicate the "last updated" time for the data displayed. For DuckDB, direct reads are fast, so this is less of an issue than with a remote database.

## Dependencies
- A Python web framework:
    - `streamlit` (recommended for speed of development and data focus)
    - OR `flask` (and `jinja2` for templates)
    - OR `fastapi` (and `uvicorn` for serving)
- `pandas` (likely for data manipulation before display).
- `duckdb` (for connecting to the database).
- Potentially a charting library if not built into the chosen framework (e.g., `matplotlib` or `plotly` if using Flask/FastAPI, though Streamlit has good built-ins).
