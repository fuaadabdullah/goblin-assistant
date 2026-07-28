import { buildCatchAllProxyHandlers } from '@/server/backendProxyRoute';

const handlers = buildCatchAllProxyHandlers();

export const { GET, POST, PUT, PATCH, DELETE } = handlers;
