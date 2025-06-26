"""Command-line interface for CausaGanha."""
import argparse
import sys

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CausaGanha - Judicial Decision Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pipeline commands (keep existing interface)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run pipeline operations')
    pipeline_parser.add_argument('action', choices=['collect', 'extract', 'update', 'run', 'archive'])
    pipeline_parser.add_argument('--date', help='Date to process (YYYY-MM-DD)')
    pipeline_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    pipeline_parser.add_argument('--archive-type', choices=['daily', 'weekly', 'monthly'], help='Archive type')
    
    # Database commands
    db_parser = subparsers.add_parser('db', help='Database operations')
    db_parser.add_argument('action', choices=['migrate', 'status', 'backup'])
    
    # Downloader commands
    download_parser = subparsers.add_parser('download', help='Download PDFs')
    download_parser.add_argument('--latest', action='store_true', help='Download latest PDF')
    download_parser.add_argument('--date', help='Download PDF for specific date')
    
    # Extractor commands
    extract_parser = subparsers.add_parser('extract', help='Extract PDF content')
    extract_parser.add_argument('--pdf-file', required=True, help='PDF file to extract')
    
    args = parser.parse_args()
    
    if args.command == 'pipeline':
        handle_pipeline_command(args)
    elif args.command == 'db':
        handle_db_command(args)
    elif args.command == 'download':
        handle_download_command(args)
    elif args.command == 'extract':
        handle_extract_command(args)
    else:
        parser.print_help()

def handle_pipeline_command(args):
    """Handle pipeline commands."""
    # Import here to avoid circular imports
    from pipeline import main as pipeline_main
    
    # Set up sys.argv to match expected format
    sys.argv = ['pipeline.py', args.action]
    if args.date:
        sys.argv.extend(['--date', args.date])
    if args.dry_run:
        sys.argv.append('--dry-run')
    if hasattr(args, 'archive_type') and args.archive_type:
        sys.argv.extend(['--archive-type', args.archive_type])
    
    pipeline_main()

def handle_db_command(args):
    """Handle database commands."""
    if args.action == 'migrate':
        from migration_runner import run_migrations
        run_migrations()
    elif args.action == 'status':
        from database import CausaGanhaDB
        db = CausaGanhaDB()
        print("Database status: Connected")
        print(f"Database path: {db.db_path}")
    elif args.action == 'backup':
        from r2_storage import backup_database
        backup_database()

def handle_download_command(args):
    """Handle download commands."""
    from downloader import main as downloader_main
    
    sys.argv = ['downloader.py']
    if args.latest:
        sys.argv.append('--latest')
    if args.date:
        sys.argv.extend(['--date', args.date])
    
    downloader_main()

def handle_extract_command(args):
    """Handle extract commands."""
    from extractor import main as extractor_main
    
    sys.argv = ['extractor.py', '--pdf_file', args.pdf_file]
    extractor_main()

if __name__ == "__main__":
    main()