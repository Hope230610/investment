import express from "express";
import type { Request, Response } from "express";
import path from "path";
import { createServer as createViteServer } from "vite";


const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";


async function proxyApiRequest(req: Request, res: Response) {
  try {
    const targetUrl = new URL(req.originalUrl, BACKEND_BASE_URL);
    const headers = new Headers();
    const hopByHopHeaders = new Set([
      'host',
      'connection',
      'content-length',
      'transfer-encoding',
      'keep-alive',
      'proxy-authenticate',
      'proxy-authorization',
      'te',
      'trailer',
      'upgrade',
    ]);

    for (const [key, value] of Object.entries(req.headers)) {
      if (!value || hopByHopHeaders.has(key.toLowerCase())) {
        continue;
      }

      headers.set(key, Array.isArray(value) ? value.join(', ') : String(value));
    }

    const init: RequestInit = {
      method: req.method,
      headers,
      redirect: "follow",
    };

    if (!["GET", "HEAD"].includes(req.method) && req.body && Object.keys(req.body).length > 0) {
      init.body = JSON.stringify(req.body);
    }

    const upstream = await fetch(targetUrl, init);
    for (const [key, value] of upstream.headers.entries()) {
      if (hopByHopHeaders.has(key.toLowerCase())) {
        continue;
      }

      res.setHeader(key, value);
    }

    res.status(upstream.status).send(Buffer.from(await upstream.arrayBuffer()));
  } catch (error) {
    console.error("API proxy failed:", error);
    res.status(502).json({
      detail: `Backend service unavailable. Make sure FastAPI is running at ${BACKEND_BASE_URL}.`,
    });
  }
}


async function startServer() {
  const app = express();
  const port = 3000;

  app.use(express.json());
  app.use("/api", proxyApiRequest);

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(port, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${port}`);
    console.log(`Proxying API requests to ${BACKEND_BASE_URL}`);
  });
}


startServer();
