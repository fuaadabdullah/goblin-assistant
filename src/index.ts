import { greet } from "./lib/greet";

// CLI entrypoint — avoid noisy logs when running tests
if (process.env.NODE_ENV !== "test") {
  greet();
}

export default greet;
