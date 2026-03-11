export function buildUserResponse(user: { email: string; phone: string }) {
  return { email: user.email, phone: user.phone };
}

export async function saveUserRecord(repo: any, user: { id: string }) {
  await repo.update(user.id, user);
  return true;
}

export function exportUserData(path: string, payload: string) {
  const fs = require("fs");
  fs.writeFileSync(path, payload);
}
