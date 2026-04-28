import { promises as fs } from "fs";
import path from "path";

const DB_DIR = path.join(process.cwd(), ".db");

async function readDB(name: string) {
  try {
    const data = await fs.readFile(path.join(DB_DIR, `${name}.json`), "utf-8");
    return JSON.parse(data);
  } catch {
    return {};
  }
}

async function writeDB(name: string, data: any) {
  await fs.mkdir(DB_DIR, { recursive: true });
  await fs.writeFile(path.join(DB_DIR, `${name}.json`), JSON.stringify(data, null, 2));
}

export const db = {
  async get(name: string) { return readDB(name); },
  async set(name: string, data: any) { return writeDB(name, data); },
};
export { readDB, writeDB };
