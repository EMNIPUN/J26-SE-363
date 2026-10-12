function matches(pathname, to) {
  return pathname === to || pathname.startsWith(`${to}/`)
}

// Builds the top-bar trail from the same nav tree the sidebar renders, so a
// page's location reads the same in both places. The longest match wins.
export function getPageTrail(sections, pathname) {
  let best = null
  for (const section of sections) {
    if (section.to && matches(pathname, section.to)) {
      if (!best || section.to.length > best.length) {
        best = { length: section.to.length, trail: [section.label], depth: pathname.length > section.to.length }
      }
    }
    for (const child of section.children ?? []) {
      if (matches(pathname, child.to) && (!best || child.to.length > best.length)) {
        best = {
          length: child.to.length,
          trail: [section.label, child.label],
          depth: pathname.length > child.to.length,
        }
      }
    }
  }
  if (!best) return []
  return best.depth ? [...best.trail, 'Details'] : best.trail
}
