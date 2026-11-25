import { fetchCached, listKey } from './cache'
import { customersApi } from './customers'
import { getDashboard } from './dashboard'
import { inboxApi } from './inbox'
import { materialsApi } from './materials'
import { ocrApi } from './ocr'
import { purchaseOrdersApi } from './purchaseOrders'
import { supplyApi } from './supply'

// The first page of each menu list, with the same filters the page itself starts with.
const LISTS = [
  [inboxApi.list, { ordering: '-received_at' }],
  [ocrApi.list, {}],
  [purchaseOrdersApi.list, { ordering: '-po_date' }],
  [purchaseOrdersApi.list, { status: ['pending', 'partial'], ordering: 'delivery_date' }],
  [supplyApi.list, { ordering: '-supply_date' }],
  [customersApi.list, { ordering: 'name' }],
  [materialsApi.list, { ordering: 'name' }],
]

/** Loads menu pages in the background, one at a time so the page on screen is not slowed down. */
export async function prefetchPages() {
  await fetchCached('dashboard', getDashboard).catch(() => {})
  for (const [list, initial] of LISTS) {
    const params = { page: 1, page_size: 10, ...initial }
    await fetchCached(listKey(list, params), () => list(params)).catch(() => {})
  }
}
