#include "molecule/mm_expand.h"

#include "molecule/ket_document.h"
#include "molecule/ket_objects.h"
#include "molecule/molecule.h"

#include <algorithm>
#include <cmath>
#include <graph/graph.h>
#include <map>
#include <optional>
#include <queue>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

float const DEFAULT_DIMENSION = 3.0f;

namespace indigo
{

    struct NeighborSpec
    {
        std::string monomerId;
        std::string attachmentPointId; // neighbors IDs
        float angle = 0.0f;            // neighbor angle in absolute coordinates
    };

    // [Uncountable] Map each monomer id to its position in monomersIds(), the order that dimensions and the graph vertices follow.
    // Ketcher writes ids that are neither sequential nor zero-based (e.g. "635"), so an id cannot be used as an index.
    using MonomerIndex = std::unordered_map<std::string, int>;

    static MonomerIndex getMonomerIndex(KetDocument& mol)
    {
        MonomerIndex index;
        const auto& ids = mol.monomersIds();
        for (size_t i = 0; i < ids.size(); ++i)
            index.emplace(ids[i], static_cast<int>(i));
        return index;
    }

    // [Uncountable] Monomer id at a connection endpoint, or an empty string when the endpoint is a molecule atom.
    // Endpoints name monomers by ref ("monomer635"), which is not always "monomer" + id.
    static std::string endpointMonomerId(KetDocument& mol, const KetConnectionEndPoint& ep)
    {
        if (!hasKetStrProp(ep, monomerId))
            return std::string();
        return mol.monomerIdByRef(getKetStrProp(ep, monomerId));
    }

    // [Uncountable] The selected flag has a different index in each monomer class, so read it through the real class.
    static bool isMonomerSelected(const KetBaseMonomer& mon)
    {
        if (mon.monomerType() == KetBaseMonomer::MonomerType::Monomer)
            return isKetBoolPropTrue(static_cast<const KetMonomer&>(mon), selected);
        return isKetBoolPropTrue(static_cast<const KetAmbiguousMonomer&>(mon), selected);
    }

    // [Uncountable] Location of a leaving-group atom, checked against the template's atom count.
    static const std::optional<Vec3f>& leavingGroupAtomLocation(const MonomerTemplate& tmpl, int atom_idx)
    {
        if (atom_idx < 0 || static_cast<size_t>(atom_idx) >= tmpl.atoms().size())
            throw Exception("monomer template '%s': leaving group atom %d is out of range (%d atoms)", tmpl.id().c_str(), atom_idx,
                            static_cast<int>(tmpl.atoms().size()));
        return tmpl.atoms()[atom_idx]->location();
    }

    // Set the expanded monomers and calculate the dimensions for each monomer as R1-R2 distance
    void getDimensions(KetDocument& mol, std::vector<float>& dimensions)
    {
        bool has_selection = false;
        for (const auto& monomerId : mol.monomersIds())
        {
            if (isMonomerSelected(*mol.getMonomerById(monomerId)))
            {
                has_selection = true;
                break;
            }
        }
        for (const auto& monomerId : mol.monomersIds())
        {
            auto& monPtr = mol.getMonomerById(monomerId);

            // Skip if the monomer is not a monomer really
            if (monPtr->monomerType() != KetBaseMonomer::MonomerType::Monomer)
            {
                dimensions.push_back(DEFAULT_DIMENSION);
                continue;
            }
            auto& mon = static_cast<KetMonomer&>(*monPtr);
            if (has_selection && !isKetBoolPropTrue(mon, selected))
            {
                dimensions.push_back(DEFAULT_DIMENSION);
            }
            else
            {
                setKetBoolProp(mon, expanded, true);
                const auto& tmpl = mol.templates().at(mon.templateId());
                // collect all leaving-group atom indices
                std::vector<int> leaves;
                for (const auto& ap_pair : tmpl.attachmentPoints())
                {
                    auto lg = ap_pair.second.leavingGroup();
                    if (lg && !lg->empty())
                        leaves.push_back(lg->at(0));
                }
                float dim = 0.0f;
                if (leaves.size() >= 2)
                {
                    // take first two for R1 and R2
                    auto loc1 = leavingGroupAtomLocation(tmpl, leaves[0]);
                    auto loc2 = leavingGroupAtomLocation(tmpl, leaves[1]);
                    if (loc1.has_value() && loc2.has_value())
                    {
                        auto v1 = loc1.value(), v2 = loc2.value();
                        float dx = v2.x - v1.x;
                        float dy = v2.y - v1.y;
                        dim = std::sqrt(dx * dx + dy * dy);
                    }
                }
                else if (leaves.size() == 1)
                {
                    // single R-group: double distance to geometric center
                    auto loc = leavingGroupAtomLocation(tmpl, leaves[0]);
                    if (loc.has_value())
                    {
                        Vec2f center{0, 0};
                        int count = 0;
                        for (const auto& atomPtr : tmpl.atoms())
                        {
                            auto aloc = atomPtr->location();
                            if (aloc.has_value())
                            {
                                center.x += aloc.value().x;
                                center.y += aloc.value().y;
                                ++count;
                            }
                        }
                        if (count > 0)
                        {
                            center.x /= count;
                            center.y /= count;
                            float dx = loc.value().x - center.x;
                            float dy = loc.value().y - center.y;
                            dim = 2.0f * std::sqrt(dx * dx + dy * dy);
                        }
                    }
                }
                dimensions.push_back(dim);
            }
        }
    }

    // Get neighbor map
    void getNeighbors(KetDocument& mol, std::unordered_map<std::string, std::vector<NeighborSpec>>& neighborMap)
    {
        // neighbor numbers
        for (const auto& conn : mol.connections())
        {
            // [Uncountable] A bond to a molecule atom has no monomer at one end and takes no part in the monomer layout.
            // Nor does a hydrogen bond: it has no attachment points, and between two strands it closes rings that overlap them.
            if (conn.connectionType() == KetConnectionHydro)
                continue;
            std::string id1 = endpointMonomerId(mol, conn.ep1());
            std::string id2 = endpointMonomerId(mol, conn.ep2());
            if (id1.empty() || id2.empty() || id1 == id2)
                continue;
            // capture attachment point (R-group) for each endpoint
            std::string ap1 = hasKetStrProp(conn.ep1(), attachmentPointId) ? getKetStrProp(conn.ep1(), attachmentPointId) : std::string();
            std::string ap2 = hasKetStrProp(conn.ep2(), attachmentPointId) ? getKetStrProp(conn.ep2(), attachmentPointId) : std::string();
            neighborMap[id1].push_back(NeighborSpec{id2, ap1});
            neighborMap[id2].push_back(NeighborSpec{id1, ap2});
        }

        // neighbor angles
        for (const auto& monId : mol.monomersIds())
        {
            Vec2f pos = mol.getMonomerById(monId)->position().value_or(Vec2f{0, 0});
            auto it = neighborMap.find(monId);
            if (it == neighborMap.end())
                continue;
            auto& specs = it->second;
            for (auto& spec : specs)
            {
                Vec2f npos = mol.getMonomerById(spec.monomerId)->position().value_or(Vec2f{0, 0});
                Vec2f v{npos.x - pos.x, npos.y - pos.y};
                spec.angle = std::atan2(v.y, v.x);
            }
        }
    }

    // Workaround to get the graph of macromolecule and use it for ring detection as for small molecules
    void getGraph(KetDocument& mol, const MonomerIndex& index, Graph& graph)
    {
        size_t n = mol.monomersIds().size();
        for (size_t i = 0; i < n; ++i)
            graph.addVertex();
        for (const auto& conn : mol.connections())
        {
            // [Uncountable] Vertices are monomer indexes, not ids. Skip molecule bonds, hydrogen bonds (see getNeighbors),
            // and a second bond between the same two monomers.
            if (conn.connectionType() == KetConnectionHydro)
                continue;
            std::string id1 = endpointMonomerId(mol, conn.ep1());
            std::string id2 = endpointMonomerId(mol, conn.ep2());
            if (id1.empty() || id2.empty())
                continue;
            int a = index.at(id1);
            int b = index.at(id2);
            if (a != b && !graph.haveEdge(a, b))
                graph.addEdge(a, b);
        }
    }

    // Place ring monomers on circles
    void placeRingMonomers(KetDocument& mol, const std::vector<float>& dimensions, Graph& graph, std::unordered_map<std::string, Vec2f>& newPositions,
                           std::unordered_set<std::string>& placed)
    {
        const auto& ids = mol.monomersIds();
        int ringCount = graph.sssrCount();
        for (int ci = 0; ci < ringCount; ++ci)
        {
            auto& verts = graph.sssrVertices(ci);
            std::vector<int> cycle;
            for (int vi = verts.begin(); vi != verts.end(); vi = verts.next(vi))
                cycle.push_back(verts[vi]);
            auto cycleSize = cycle.size();
            if (cycleSize < 2)
                continue;
            float phi = 2.0f * static_cast<float>(M_PI) / cycleSize;
            float R = 0;
            for (size_t i = 0; i < cycleSize; ++i)
            {
                int u = cycle[i], v = cycle[(i + 1) % cycleSize];
                float d = (dimensions[u] + dimensions[v]) * 0.5f;
                float r = d / (2 * std::sin(phi / 2));
                R = std::max(R, r);
            }
            Vec2f center{0, 0};
            for (auto idx : cycle)
            {
                Vec2f p = mol.getMonomerById(ids[idx])->position().value_or(Vec2f{0, 0});
                center.x += p.x;
                center.y += p.y;
            }
            center.x /= cycleSize;
            center.y /= cycleSize;
            for (size_t i = 0; i < cycleSize; ++i)
            {
                float ang = i * phi;
                Vec2f pos{center.x + R * std::cos(ang), center.y + R * std::sin(ang)};
                const auto& id = ids[cycle[i]];
                newPositions[id] = pos;
                placed.insert(id);
            }
        }
    }

    // BFS (Breadth First Search) for a Graph propagate positions for non-ring monomers
    void bfsPropagate(KetDocument& mol, const MonomerIndex& index, const std::vector<float>& dimensions,
                      const std::unordered_map<std::string, std::vector<NeighborSpec>>& adjacency, std::unordered_map<std::string, Vec2f>& newPos,
                      std::unordered_set<std::string>& placed)
    {
        // [Sapio] FR-48004 Expose expandedMonomersToAtoms to Python API.
        // Guard at function entry: if there are no monomers, there's nothing to propagate.
        // This prevents crashes when expandedMonomersToAtoms() has already converted all monomers to atoms.
        const auto& monomer_ids = mol.monomersIds();
        if (monomer_ids.size() == 0)
        {
            return; // No monomers, nothing to propagate
        }

        std::queue<std::string> q;
        for (auto& id : placed)
            q.push(id);
        // [Uncountable] Seed every connected component that has no ring, not only the first monomer.
        // A component left unplaced has no entry in newPos, and applyTransformations then fails on it.
        auto next_start = monomer_ids.begin();
        while (true)
        {
            if (q.empty())
            {
                while (next_start != monomer_ids.end() && placed.count(*next_start))
                    ++next_start;
                if (next_start == monomer_ids.end())
                    break;
                const auto& start = *next_start;
                newPos[start] = mol.getMonomerById(start)->position().value_or(Vec2f{0, 0});
                placed.insert(start);
                q.push(start);
            }
            auto cur = q.front();
            q.pop();
            Vec2f cp = newPos[cur];
            float du = dimensions[index.at(cur)];
            auto it = adjacency.find(cur);
            if (it == adjacency.end())
                continue;
            for (size_t i = 0; i < it->second.size(); ++i)
            {
                const auto& spec = it->second[i];
                const auto& nid = spec.monomerId;
                if (placed.count(nid))
                    continue;
                float dv = dimensions[index.at(nid)];
                float dist = (du + dv) * 0.5f;
                float ang = spec.angle; // use precomputed angle
                Vec2f pos{cp.x + dist * std::cos(ang), cp.y + dist * std::sin(ang)};
                newPos[nid] = pos;
                placed.insert(nid);
                q.push(nid);
            }
        }
    }

    // Normalize angle to [-pi,pi]
    float normalizeAngle(float a)
    {
        const float PI2 = 2.0f * static_cast<float>(M_PI);
        a = fmod(a, PI2);
        if (a > static_cast<float>(M_PI))
            a -= PI2;
        else if (a < -static_cast<float>(M_PI))
            a += PI2;
        return a;
    }

    // Evaluate perpendicular distance of rotated leaving-group atoms to the given line (ignoring translation)
    float evalLeavingDistance(const Vec2f& pBase, const Vec2f& p0, const Vec2f& p1, const Vec2f& v1, const Vec2f& v2, float rot)
    {
        float c = std::cos(rot), s = std::sin(rot);
        Vec2f a0{c * v1.x - s * v1.y + pBase.x, s * v1.x + c * v1.y + pBase.y};
        Vec2f a1{c * v2.x - s * v2.y + pBase.x, s * v2.x + c * v2.y + pBase.y};
        Vec2f cen0{(pBase.x + p0.x) / 2, (pBase.y + p0.y) / 2};
        Vec2f cen1{(pBase.x + p1.x) / 2, (pBase.y + p1.y) / 2};
        Vec2f d0{a0.x - cen0.x, a0.y - cen0.y};
        Vec2f d1{cen1.x - a1.x, cen1.y - a1.y};

        return std::sqrt(d0.x * d0.x + d0.y * d0.y) + std::sqrt(d1.x * d1.x + d1.y * d1.y);
    }

    // Decide optimal rotation based on two key attachment points (R1/R2 or fallback pairs)
    static void computeRotations(KetDocument& mol, const std::unordered_map<std::string, std::vector<NeighborSpec>>& neighborMap,
                                 std::unordered_map<std::string, float>& newAngles)
    {
        for (const auto& id : mol.monomersIds())
        {
            // [Uncountable] An ambiguous monomer is a KetAmbiguousMonomer, not a KetMonomer, and has no single template to rotate.
            auto& monPtr = mol.getMonomerById(id);
            if (monPtr->monomerType() != KetBaseMonomer::MonomerType::Monomer)
                continue;
            auto& m = static_cast<KetMonomer&>(*monPtr);
            Vec2f pBase = m.position().value_or(Vec2f{0, 0});
            // find neighbors for this monomer
            auto itAdj = neighborMap.find(id);
            if (itAdj == neighborMap.end() || itAdj->second.size() < 2)
            {
                // not enough neighbors to define direction
                newAngles[id] = 0.0f;
                continue;
            }
            auto& specs = itAdj->second;
            // map AP id -> index
            std::unordered_map<std::string, size_t> idxMap;
            for (size_t i = 0; i < specs.size(); ++i)
                idxMap[specs[i].attachmentPointId] = i;
            // pick two AP keys: prefer R1/R2, else R1/R3, else R2/R3, else first two
            std::string ap1, ap2;
            if (idxMap.count("R1") && idxMap.count("R2"))
            {
                ap1 = "R1";
                ap2 = "R2";
            }
            else if (idxMap.count("R1") && idxMap.count("R3"))
            {
                ap1 = "R1";
                ap2 = "R3";
            }
            else if (idxMap.count("R2") && idxMap.count("R3"))
            {
                ap1 = "R2";
                ap2 = "R3";
            }
            else
            {
                ap1 = specs[0].attachmentPointId;
                ap2 = specs[1].attachmentPointId;
            }
            // compute neighbor positions
            auto& spec0 = specs[idxMap[ap1]];
            auto& spec1 = specs[idxMap[ap2]];
            Vec2f n0 = mol.getMonomerById(spec0.monomerId)->position().value_or(pBase);
            Vec2f n1 = mol.getMonomerById(spec1.monomerId)->position().value_or(pBase);
            // get leaving-group axis in template coords
            const auto& tmpl = mol.templates().at(m.templateId());
            const auto& appts = tmpl.attachmentPoints();
            auto ap1_it = appts.find(ap1);
            auto ap2_it = appts.find(ap2);
            if (ap1_it == appts.end() || ap2_it == appts.end())
            {
                newAngles[id] = 0.0f;
                continue;
            }
            auto lg1 = ap1_it->second.leavingGroup();
            auto lg2 = ap2_it->second.leavingGroup();
            if (!lg1 || !lg2 || lg1->empty() || lg2->empty())
            {
                newAngles[id] = 0.0f;
                continue;
            }
            auto loc1_opt = leavingGroupAtomLocation(tmpl, lg1->at(0));
            auto loc2_opt = leavingGroupAtomLocation(tmpl, lg2->at(0));
            if (!loc1_opt.has_value() || !loc2_opt.has_value())
            {
                newAngles[id] = 0.0f;
                continue;
            }
            Vec2f loc1{loc1_opt->x, loc1_opt->y};
            Vec2f loc2{loc2_opt->x, loc2_opt->y};
            Vec2f vR{loc2.x - loc1.x, loc2.y - loc1.y};
            float angleR = std::atan2(vR.y, vR.x);
            Vec2f vN{n1.x - n0.x, n1.y - n0.y};
            float angleN = std::atan2(vN.y, vN.x);
            float r1 = normalizeAngle(angleN - angleR);
            float r2 = normalizeAngle(angleN - (angleR + static_cast<float>(M_PI)));
            float d1 = evalLeavingDistance(pBase, n0, n1, loc1, loc2, r1);
            float d2 = evalLeavingDistance(pBase, n0, n1, loc1, loc2, r2);
            newAngles[id] = (d1 < d2) ? r1 : r2;
        }
    }

    // Apply transformations to monomers: align leaving-group axis with neighbor line and shift to new positions
    void applyTransformations(KetDocument& mol, const std::unordered_map<std::string, Vec2f>& newPos, const std::unordered_map<std::string, float>& newAngles)
    {
        for (const auto& id : mol.monomersIds())
        {
            // [Uncountable] Only a KetMonomer stores a transformation. Casting an ambiguous monomer wrote past the end of it.
            auto& monPtr = mol.getMonomerById(id);
            if (monPtr->monomerType() != KetBaseMonomer::MonomerType::Monomer)
                continue;
            auto& m = static_cast<KetMonomer&>(*monPtr);
            // determine rotation
            float rotation = 0.0f;
            auto it = newAngles.find(id);
            if (it != newAngles.end())
                rotation = it->second;
            // compute shift as difference from original position
            Vec2f newP = newPos.at(id);
            Vec2f origP = m.position().value_or(Vec2f{0, 0});
            Vec2f shift{newP.x - origP.x, newP.y - origP.y};
            m.setTransformation({rotation, shift});
        }
    }

    void indigoExpand(KetDocument& mol)
    {
        // [Sapio] FR-48004 Expose expandedMonomersToAtoms to Python API.
        // Early return if there are no monomers to expand. This prevents crashes
        // when expandedMonomersToAtoms() has already converted all monomers to atoms.
        // This is a valid state - a molecule with no monomers has nothing to expand.
        const auto& monomer_ids = mol.monomersIds();
        if (monomer_ids.size() == 0)
        {
            return; // No monomers to expand, nothing to do
        }

        // fill all required for calculations
        MonomerIndex index = getMonomerIndex(mol);                              // monomer id -> position in monomersIds()
        std::vector<float> dimensions;                                          // R1-R2 distance, by monomer index
        std::unordered_map<std::string, std::vector<NeighborSpec>> neighborMap; // monomerId -> neighbors with R-group info
        Graph graph;                                                            // workaround to run sssr for macromolecule
        getDimensions(mol, dimensions);
        getNeighbors(mol, neighborMap);
        getGraph(mol, index, graph);

        // calculate new positions for ring monomers and non ring monomers
        std::unordered_map<std::string, Vec2f> newPositions;
        std::unordered_map<std::string, float> newAngles;
        std::unordered_set<std::string> placed;
        placeRingMonomers(mol, dimensions, graph, newPositions, placed);
        bfsPropagate(mol, index, dimensions, neighborMap, newPositions, placed);
        computeRotations(mol, neighborMap, newAngles);

        // transforming the output
        applyTransformations(mol, newPositions, newAngles);
    }

} // namespace indigo
