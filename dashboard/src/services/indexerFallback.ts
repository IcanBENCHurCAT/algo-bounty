import algosdk from 'algosdk'
import { getNetworkName, getAlgodClient } from '@/lib/algorand'
import type { Bounty, BountyStatus } from '@/types'

const INDEXER_URLS = {
  testnet: 'https://testnet-idx.algonode.cloud',
  mainnet: 'https://mainnet-idx.algonode.cloud',
  localnet: 'http://localhost:8980',
}

export function getIndexerUrl(): string {
  const network = getNetworkName()
  return INDEXER_URLS[network] || INDEXER_URLS.testnet
}

async function readBoxBytes(algodClient: algosdk.Algodv2, appId: number, name: string): Promise<Uint8Array | null> {
  try {
    const encoder = new TextEncoder()
    const nameBytes = encoder.encode(name)
    const resp = await algodClient.getApplicationBoxByName(appId, nameBytes).do()
    return resp.value
  } catch (e) {
    return null
  }
}

async function readBoxUInt64(algodClient: algosdk.Algodv2, appId: number, name: string): Promise<number | null> {
  const bytes = await readBoxBytes(algodClient, appId, name)
  if (!bytes || bytes.length !== 8) return null
  let val = BigInt(0)
  for (let i = 0; i < 8; i++) {
    val = (val * BigInt(256)) + BigInt(bytes[i])
  }
  return Number(val)
}

async function readBoxString(algodClient: algosdk.Algodv2, appId: number, name: string): Promise<string | null> {
  const bytes = await readBoxBytes(algodClient, appId, name)
  if (!bytes) return null
  return new TextDecoder().decode(bytes)
}

async function readBoxAddress(algodClient: algosdk.Algodv2, appId: number, name: string): Promise<string | null> {
  const bytes = await readBoxBytes(algodClient, appId, name)
  if (!bytes || bytes.length !== 32) return null
  return algosdk.encodeAddress(bytes)
}

export async function fetchBountyFromChain(appId: number): Promise<Bounty> {
  const client = getAlgodClient()
  
  const [
    stateVal,
    bountyIdBytes,
    escrowAmountVal,
    assetIdVal,
    creatorAddr,
    agentAddr,
    isHitmVal,
    proofUrlVal,
  ] = await Promise.all([
    readBoxUInt64(client, appId, 'state'),
    readBoxBytes(client, appId, 'bounty_id'),
    readBoxUInt64(client, appId, 'escrow_amount'),
    readBoxUInt64(client, appId, 'asset_id'),
    readBoxAddress(client, appId, 'creator_address'),
    readBoxAddress(client, appId, 'agent_address'),
    readBoxUInt64(client, appId, 'is_hitm'),
    readBoxString(client, appId, 'proof_url'),
  ])

  if (stateVal === null && bountyIdBytes === null) {
    throw new Error('Application not found or not an AlgoBounty contract')
  }

  const bountyId = bountyIdBytes ? new TextDecoder().decode(bountyIdBytes) : `b_${appId}`

  const statusMap: Record<number, BountyStatus> = {
    0: 'open',
    1: 'claimed',
    2: 'submitted',
    3: 'open',
    4: 'disputed',
    5: 'closed',
    6: 'closed',
    7: 'open',
  }

  const status = statusMap[stateVal ?? 0] ?? 'open'

  return {
    bounty_id: bountyId,
    app_id: appId,
    status,
    creator: creatorAddr || '',
    worker: agentAddr || null,
    amount: escrowAmountVal ?? 0,
    asset_id: assetIdVal ?? 0,
    asset_name: assetIdVal === 0 ? 'ALGO' : `ASA-${assetIdVal}`,
    hitm: isHitmVal === 1,
    deadline_round: null,
    deadline_rounds_remaining: null,
    deadline_timestamp: null,
    description: `Bounty #${bountyId} (Fetched direct from Algorand smart contract)`,
    repo_url: proofUrlVal || null,
    repo_labels: [],
    karma_required: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    tags: [],
    github_issue: null,
  }
}

export async function fetchBountiesFromChain(): Promise<Bounty[]> {
  const indexerUrl = getIndexerUrl()
  const url = `${indexerUrl}/v2/applications?limit=50`
  
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to fetch applications from indexer: ${response.statusText}`)
  }
  
  const data = await response.json()
  const apps = data.applications || data.apps || []
  const bounties: Bounty[] = []
  
  // Resolve them concurrently up to a limit
  const promises = apps.map(async (app: any) => {
    const appId = app.id
    try {
      const boxesUrl = `${indexerUrl}/v2/applications/${appId}/boxes?limit=5`
      const boxesResp = await fetch(boxesUrl)
      if (!boxesResp.ok) return null
      
      const boxesData = await boxesResp.json()
      const boxes = boxesData.boxes || []
      
      const hasStateBox = boxes.some((b: any) => b.name === 'c3RhdGU=' || b.name === 'Ym91bnR5X2lk')
      if (hasStateBox) {
        return await fetchBountyFromChain(appId)
      }
    } catch (e) {
      // ignore
    }
    return null
  })

  const results = await Promise.all(promises)
  for (const item of results) {
    if (item) {
      bounties.push(item)
    }
  }
  
  return bounties
}
