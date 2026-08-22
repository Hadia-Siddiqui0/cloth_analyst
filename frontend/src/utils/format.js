export function rupees(n) {
  if (n === null || n === undefined) return "Not available";
  return "Rs. " + Math.round(Math.abs(n)).toLocaleString();
}

export function signedRupees(n) {
  if (n === null || n === undefined) return "Not available";
  return (n < 0 ? "-" : "") + rupees(n);
}
