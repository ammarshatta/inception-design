// Tiny IndexedDB helper (no dependency): two stores, "queue" (offline actions) and "cache" (reads).
const DB_NAME = 'cc-portal'
const VERSION = 1
let dbPromise: Promise<IDBDatabase> | null = null

function open(): Promise<IDBDatabase> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, VERSION)
      req.onupgradeneeded = () => {
        const db = req.result
        if (!db.objectStoreNames.contains('queue')) db.createObjectStore('queue', { keyPath: 'uuid' })
        if (!db.objectStoreNames.contains('cache')) db.createObjectStore('cache')
      }
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })
  }
  return dbPromise
}

function wrap<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function idbGet<T = any>(store: string, key: IDBValidKey): Promise<T | undefined> {
  const db = await open()
  return wrap(db.transaction(store).objectStore(store).get(key))
}
export async function idbPut(store: string, value: any, key?: IDBValidKey): Promise<void> {
  const db = await open()
  await wrap(db.transaction(store, 'readwrite').objectStore(store).put(value, key))
}
export async function idbDelete(store: string, key: IDBValidKey): Promise<void> {
  const db = await open()
  await wrap(db.transaction(store, 'readwrite').objectStore(store).delete(key))
}
export async function idbAll<T = any>(store: string): Promise<T[]> {
  const db = await open()
  return wrap(db.transaction(store).objectStore(store).getAll())
}
