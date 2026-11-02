import { setupServer } from "msw/node";

/** Server tiruan untuk test; handler ditambahkan per test dengan server.use(...). */
export const server = setupServer();
