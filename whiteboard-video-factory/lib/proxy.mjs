// 让 Node 的 fetch 走 HTTPS_PROXY / HTTP_PROXY（undici 的 fetch 默认不读代理环境变量）。
// 只在本机有代理时才接管，其它平台/无代理环境下 installProxyFetch() 是空操作。
// 用途：commons.wikimedia.org / upload.wikimedia.org 在部分网络下必须经代理才能访问。
import http from "node:http";
import https from "node:https";
import tls from "node:tls";

const PROXY = process.env.HTTPS_PROXY || process.env.https_proxy
  || process.env.HTTP_PROXY || process.env.http_proxy || "";

function tunnel(proxyUrl, host, port) {
  return new Promise((resolve, reject) => {
    const u = new URL(proxyUrl);
    const req = http.request({
      host: u.hostname,
      port: u.port || (u.protocol === "https:" ? 443 : 80),
      method: "CONNECT",
      path: `${host}:${port}`,
      headers: { Host: `${host}:${port}` },
    });
    req.on("connect", (res, socket) =>
      res.statusCode === 200 ? resolve(socket) : reject(new Error(`proxy CONNECT ${res.statusCode}`)));
    req.on("error", reject);
    req.end();
  });
}

export async function proxyFetch(url, init = {}) {
  if (!PROXY) return fetch(url, init);
  const u = new URL(url);
  const isHttps = u.protocol === "https:";
  const port = u.port || (isHttps ? 443 : 80);
  const socket = await tunnel(PROXY, u.hostname, port);
  const mod = isHttps ? https : http;
  return await new Promise((resolve, reject) => {
    const req = mod.request({
      host: u.hostname,
      port,
      path: u.pathname + u.search,
      method: init.method || "GET",
      headers: init.headers || {},
      servername: isHttps ? u.hostname : undefined,
      createConnection: () => (isHttps ? tls.connect({ socket, servername: u.hostname }) : socket),
    }, (res) => {
      const chunks = [];
      res.on("data", (c) => chunks.push(c));
      res.on("end", () => resolve(new Response(Buffer.concat(chunks), { status: res.statusCode, headers: res.headers })));
    });
    req.on("error", reject);
    if (init.body) req.write(init.body);
    req.end();
  });
}

export function installProxyFetch() {
  if (!PROXY) return false;
  globalThis.fetch = proxyFetch;
  return true;
}
