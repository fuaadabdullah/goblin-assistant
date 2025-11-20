export function greet(name = "Goblin") {
  const msg = `Hello from Goblin Assistant, ${name}!`;
  console.log(msg);
  return msg;
}

export default greet;
