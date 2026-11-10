import { eveChannel } from "eve/channels/eve";
import { localDev, none } from "eve/channels/auth";

// LAB ONLY: anonymous access, because the lab listens on 127.0.0.1 and no secret is involved.
// Replace `none()` with a real authenticator before you expose an agent (docs: guides/auth-and-route-protection).
export default eveChannel({
  auth: [localDev(), none()],
});
