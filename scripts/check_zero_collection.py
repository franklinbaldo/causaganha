"""Check if zero collections occurred on a Brazilian business day."""
import sys
from datetime import datetime, timedelta, timezone

def main():
    if len(sys.argv) < 2:
        print("Usage: check_zero_collection.py <uploaded_count>")
        sys.exit(1)

    try:
        uploaded = int(sys.argv[1])
    except ValueError:
        print(f"Invalid uploaded count: {sys.argv[1]}")
        sys.exit(1)

    if uploaded > 0:
        print(f"Collected {uploaded} ZIPs. Health OK.")
        sys.exit(0)

    # UPLOADED == 0
    try:
        import holidays
    except ImportError:
        print("holidays package not found.")
        sys.exit(2)

    br_tz = timezone(timedelta(hours=-3))
    today = datetime.now(br_tz).date()

    br_holidays = holidays.country_holidays('BR')

    is_weekend = today.weekday() >= 5
    is_holiday = today in br_holidays

    if is_weekend or is_holiday:
        reason = "weekend" if is_weekend else f"holiday ({br_holidays.get(today)})"
        print(f"Zero ZIPs collected, but today ({today}) is a {reason}. No alert needed.")
        sys.exit(0)

    print("🚨 CRITICAL: Zero diários coletados hoje (Dia Útil). Check proxy and DJEN status.")
    sys.exit(1)

if __name__ == "__main__":
    main()