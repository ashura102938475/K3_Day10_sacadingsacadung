import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { stitch } from "@google/stitch-sdk";

const [projectId, screenId, outputDirectory = "stitch"] = process.argv.slice(2);

if (!projectId || !screenId) {
  throw new Error(
    "Usage: npm run fetch:stitch -- <project-id> <screen-id> [output-directory]",
  );
}

if (!process.env.STITCH_API_KEY) {
  throw new Error("STITCH_API_KEY is required in the process environment.");
}

const project = stitch.project(projectId);
const screen = await project.getScreen(screenId);
const [htmlUrl, imageUrl] = await Promise.all([
  screen.getHtml(),
  screen.getImage(),
]);

const download = async (url, destination) => {
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status}) for ${destination}`);
  }
  const body = Buffer.from(await response.arrayBuffer());
  await writeFile(destination, body);
  return body.length;
};

const outputPath = path.resolve(outputDirectory);
await mkdir(outputPath, { recursive: true });

const [htmlBytes, imageBytes] = await Promise.all([
  download(htmlUrl, path.join(outputPath, "screen.html")),
  download(imageUrl, path.join(outputPath, "screen.png")),
]);

await writeFile(
  path.join(outputPath, "source.json"),
  `${JSON.stringify(
    {
      projectId,
      screenId,
      htmlFile: "screen.html",
      imageFile: "screen.png",
      downloadedAt: new Date().toISOString(),
    },
    null,
    2,
  )}\n`,
  "utf8",
);

console.log(`Downloaded Stitch screen: ${htmlBytes} HTML bytes, ${imageBytes} image bytes.`);
