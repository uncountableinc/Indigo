/****************************************************************************
 * Copyright (C) from 2009 to Present EPAM Systems.
 *
 * This file is part of Indigo toolkit.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ***************************************************************************/

#ifndef __pathway_layout_h__
#define __pathway_layout_h__molecules

#include <algorithm>
#include <cmath>
#include <fstream>
#include <functional>
#include <iostream>
#include <list>
#include <numeric>
#include <vector>

#include "reaction/pathway_reaction.h"

namespace indigo
{
    // The algorithm is based on the following paper:
    // https://www.researchgate.net/publication/30508504_Improving_Walker's_Algorithm_to_Run_in_Linear_Time
    // The original Walker's algorithm is described here:
    // https://www.researchgate.net/publication/220853707_An_Optimal_Algorithm_for_Computing_the_Trees_of_a_Directed_Graph

    class PathwayLayout
    {
        DECL_ERROR;

    public:
        PathwayLayout(PathwayReaction& reaction) : _reaction(reaction), _depths(10, 0), _maxDepth(0)
        {
        }

        void make();

    private:
        static constexpr float MARGIN = 1.f;
        static constexpr float ARROW_HEAD_WIDTH = 2.5f;
        static constexpr float ARROW_TAIL_LENGTH = 0.5f;
        static constexpr float ARROW_LENGTH = ARROW_TAIL_LENGTH + ARROW_TAIL_LENGTH;
        static constexpr float HORIZONTAL_SPACING = 3.5f;
        static constexpr float VERTICAL_SPACING = 2.5f;
        static constexpr float MULTIPATHWAY_VERTICAL_SPACING = 1.5f;

        struct PathwayLayoutItem
        {
            PathwayLayoutItem(PathwayReaction& pwr, int nodeIdx, int reactantIdx = -1)
                : levelTree(-1), prelim(0.0), mod(0.0), shift(0.0), change(0.0), width(0.0), height(0.0), ancestor(this), thread(nullptr), children(),
                  parent(nullptr), nextSibling(nullptr), prevSibling(nullptr), reaction(pwr)
            {
                auto& reactionNode = reaction.getReactionNode(nodeIdx);
                auto& simpleReaction = reaction.getReaction(reactionNode.reactionIdx);
                // create as a final reactant child
                if (reactantIdx != -1)
                {
                    auto& mol = reaction.getMolecule(reactantIdx);
                    Rect2f boundingBox;
                    mol.getBoundingBox(boundingBox);
                    molecules.push_back(std::make_pair(reactantIdx, boundingBox));
                    width = boundingBox.width();
                    height = boundingBox.height();
                }
                else
                {
                    for (auto pidx : simpleReaction.productIndexes)
                    {
                        auto& mol = reaction.getMolecule(pidx);
                        Rect2f boundingBox;
                        mol.getBoundingBox(boundingBox);
                        if (molecules.size())
                            width += MARGIN;
                        molecules.push_back(std::make_pair(pidx, boundingBox));
                        width += boundingBox.width(); // add some spacing for plus
                        height = std::max(boundingBox.height(), height);
                    }

                    // add precursors free reactants as children
                    for (int i = 0; i < simpleReaction.reactantIndexes.size(); ++i)
                    {
                        // check if it is a final reactant
                        if (!reactionNode.successorReactants.find(i))
                        {
                            auto ridx = simpleReaction.reactantIndexes[i];
                            reactantsNoPrecursors.emplace_back(reaction, nodeIdx, ridx);
                            PathwayLayoutItem* item = &reactantsNoPrecursors.back();
                            children.push_back(item);
                            item->parent = this;
                            if (children.size() > 1)
                            {
                                children[children.size() - 2]->nextSibling = item;
                                item->prevSibling = children[children.size() - 2];
                            }
                        }
                    }
                }
            }

            PathwayLayoutItem* getFirstChild()
            {
                return children.empty() ? nullptr : children.front();
            }

            PathwayLayoutItem* getLastChild()
            {
                return children.empty() ? nullptr : children.back();
            }

            void clear()
            {
                levelTree = -1;
                prelim = mod = shift = change = 0.0;
                ancestor = thread = nullptr;
            }

            void applyLayout()
            {
                if (molecules.size())
                {
                    float totalWidth = std::accumulate(molecules.begin(), molecules.end(), 0.0f,
                                                       [](float acc, const std::pair<int, Rect2f>& r) { return acc + r.second.width(); });

                    float spacing = molecules.size() > 1 ? (width - totalWidth) / (molecules.size() - 1) : (width - totalWidth) / 2;
                    float currentX = boundingBox.left();
                    float currentY = boundingBox.bottom();
                    for (auto& mol_desc : molecules)
                    {
                        auto& mol = reaction.getMolecule(mol_desc.first);
                        Vec2f item_offset(currentX - mol_desc.second.left(), currentY - mol_desc.second.bottom());
                        mol.offsetCoordinates(Vec3f(item_offset.x, item_offset.y, 0));
                        currentX += mol_desc.second.width() + spacing;
                    }
                }
            }

            void setXY(float x, float y)
            {
                boundingBox = Rect2f(Vec2f(x - width, y - height / 2), Vec2f(x, y + height / 2));
            }

            // required for the layout algorithm
            float width, height;
            std::vector<PathwayLayoutItem*> children;
            std::list<PathwayLayoutItem> reactantsNoPrecursors;
            PathwayLayoutItem* parent;
            PathwayLayoutItem* nextSibling;
            PathwayLayoutItem* prevSibling;

            // computed fields
            int levelTree;
            float prelim, mod, shift, change;
            PathwayLayoutItem* ancestor;
            PathwayLayoutItem* thread;

            // other data
            std::vector<std::pair<int, Rect2f>> molecules;
            PathwayReaction& reaction;
            Rect2f boundingBox;
        };

        struct PathwayLayoutRootItem
        {
            PathwayLayoutRootItem(int root) : rootIndex(root)
            {
            }
            int rootIndex;
            Rect2f boundingBox;
            std::vector<PathwayLayout::PathwayLayoutItem*> layoutItems;
        };

        void traverse(PathwayLayoutItem* root, std::function<void(PathwayLayoutItem*)> node_processor);

        float spacing(PathwayLayoutItem* top, PathwayLayoutItem* bottom, bool siblings)
        {
            return VERTICAL_SPACING + (top->height + bottom->height) / 2.0f;
        }

        void updateDepths(int depth, PathwayLayoutItem* item);

        void determineDepths();

        void buildLayoutTree();

        void firstWalk(PathwayLayoutItem* node, int num, int depth);

        PathwayLayoutItem* apportion(PathwayLayoutItem* currentNode, PathwayLayoutItem* ancestorNode);

        PathwayLayoutItem* nextTop(PathwayLayoutItem* node);

        PathwayLayoutItem* nextBottom(PathwayLayoutItem* node);

        void moveSubtree(PathwayLayoutItem* parent, PathwayLayoutItem* wp, float shift);

        void executeShifts(PathwayLayoutItem* node);

        PathwayLayoutItem* ancestor(PathwayLayoutItem* node1, PathwayLayoutItem* node2, PathwayLayoutItem* ancestor);

        void secondWalk(PathwayLayoutItem* node, PathwayLayoutItem* parent, float modifier, int depth);

        void applyLayout();

        std::vector<float> _depths;
        std::vector<float> _shifts;

        int _maxDepth = 0;
        PathwayReaction& _reaction;
        std::vector<PathwayLayoutItem> _layoutItems;
        std::vector<PathwayLayoutRootItem> _layoutRootItems;
    };
}

#endif