export let dbInstance: any = null;
export let connInstance: any = null;

let initializationPromise: Promise<any> | null = null;

export async function getDuckDB() {
  if (dbInstance && connInstance) {
    return { db: dbInstance, conn: connInstance };
  }

  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = (async () => {
    try {
      const duckdb = await import('@duckdb/duckdb-wasm');
      const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
      const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

      if (!bundle.mainWorker) {
        throw new Error('DuckDB bundle selection failed: No mainWorker found.');
      }

      let worker;
      try {
        worker = new Worker(bundle.mainWorker);
      } catch (workerErr) {
        console.warn('Direct Worker load failed, attempting Blob fallback...', workerErr);
        const response = await fetch(bundle.mainWorker); // Safe to use standard fetch here as it's a static JS asset, but could use fetchWithRetry
        const content = await response.text();
        const blob = new Blob([content], { type: 'application/javascript' });
        worker = new Worker(URL.createObjectURL(blob));
      }

      const logger = new duckdb.ConsoleLogger();
      dbInstance = new duckdb.AsyncDuckDB(logger, worker);
      await dbInstance.instantiate(bundle.mainModule, bundle.pthreadWorker);

      connInstance = await dbInstance.connect();
      await connInstance.query("INSTALL httpfs; LOAD httpfs;");
      await connInstance.query("SET enable_http_metadata_cache=true;");

      return { db: dbInstance, conn: connInstance };
    } catch (err) {
      initializationPromise = null; // allow retrying
      throw err;
    }
  })();

  return initializationPromise;
}
