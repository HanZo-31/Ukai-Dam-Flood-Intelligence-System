/** "Latest request wins" guard: results of an older request are ignored, never shown. */
export class LatestGuard {
  private current = 0;
  begin(): number {
    this.current += 1;
    return this.current;
  }
  isCurrent(token: number): boolean {
    return token === this.current;
  }
  invalidate(): void {
    this.current += 1;
  }
}
