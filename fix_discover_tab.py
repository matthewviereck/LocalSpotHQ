import re

def update_html_for_discover_tab(input_html='phoenixville.html', output_html='phoenixville.html'):
    """
    Update the HTML to show Discover tab with Activities and Curated Plans sections
    """
    
    print(">> Reading HTML file...")
    
    with open(input_html, 'r', encoding='utf-8') as f:
        html = f.read()
    
    print(">> Making updates...")
    
    # 1. Rename "Outings" to "Discover" in tab button
    html = html.replace(
        'switchTab(\'outings\')" id="tab-outings"',
        'switchTab(\'discover\')" id="tab-discover"'
    )
    html = html.replace(
        '>Outings</button>',
        '><i class="fa-solid fa-compass mr-1"></i> Discover</button>'
    )
    
    # 2. Add plansData array after outingsData
    if 'const plansData' not in html:
        html = re.sub(
            r'(const outingsData = \[[\s\S]*?\];)',
            r'\1\n\n        const plansData = [];',
            html
        )
        print("   * Added plansData array")
    
    # 3. Update references from 'outings' to 'discover' in JavaScript
    html = re.sub(
        r"currentTab === 'outings'",
        "currentTab === 'discover'",
        html
    )
    html = re.sub(
        r"'events', 'dining', 'outings'",
        "'events', 'dining', 'discover'",
        html
    )
    
    # 4. Find where currentTab === 'outings' render logic is and replace it
    # Look for the pattern where it renders outings
    pattern = r"if \(currentTab === 'discover'\) \{[\s\S]*?container\.innerHTML = items\.map\(\(item\)"
    
    new_logic = """if (currentTab === 'discover') {
                renderDiscoverTab(container, items);
                return;
            }
            
            container.innerHTML = items.map((item)"""
    
    if re.search(pattern, html):
        html = re.sub(pattern, new_logic, html, count=1)
    else:
        # If not found, try simpler pattern
        html = re.sub(
            r"(if \(currentTab === 'discover'\) \{)[\s\S]*?(container\.innerHTML = items\.map)",
            r"\1\n                renderDiscoverTab(container, items);\n                return;\n            }\n            \n            \2",
            html,
            count=1
        )
    
    # 5. Add renderDiscoverTab and showPlanDetails functions before the last closing script tag
    discover_functions = '''
        
        // Render Discover tab with Activities and Curated Plans sections
        function renderDiscoverTab(container, activities) {
            let html = '';
            
            // SECTION 1: ACTIVITIES
            html += `
                <div class="mb-12">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h2 class="text-2xl font-black text-slate-900">Activities & Attractions</h2>
                            <p class="text-sm text-slate-600 mt-1">Things to do around Phoenixville</p>
                        </div>
                        <span class="text-sm text-slate-500 font-bold">${activities.length} activities</span>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            `;
            
            activities.forEach(item => {
                html += `
                    <div class="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow border border-slate-100">
                        <img src="${item.img}" alt="${item.title}" class="w-full h-40 object-cover" onerror="this.src='https://placehold.co/600x400?text=No+Image'">
                        <div class="p-4">
                            <span class="text-xs font-bold px-2 py-1 rounded-full bg-slate-100 text-slate-700">${item.type || 'Activity'}</span>
                            <h3 class="font-black text-lg mt-2 mb-1 text-slate-900">${item.title}</h3>
                            ${item.desc ? `<p class="text-sm text-slate-600 mb-2">${item.desc}</p>` : ''}
                            <div class="flex items-center justify-between text-sm mt-3">
                                <span class="text-slate-500 text-xs">${item.loc}</span>
                                <span class="font-bold text-blue-600">${item.price}</span>
                            </div>
                            ${item.link ? `
                                <a href="${item.link}" target="_blank" rel="noopener" 
                                   class="block mt-3 text-blue-600 hover:text-blue-700 font-medium text-sm">
                                    Learn More <i class="fa-solid fa-arrow-right ml-1"></i>
                                </a>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
            
            // SECTION 2: CURATED PLANS
            html += `
                <div class="mt-16 pt-8 border-t-4 border-slate-200">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h2 class="text-2xl font-black text-slate-900">Curated Day Plans</h2>
                            <p class="text-sm text-slate-600 mt-1">Complete experiences with itineraries & tips</p>
                        </div>
                        <span class="text-sm text-slate-500 font-bold">${plansData.length} plans</span>
                    </div>
            `;
            
            if (plansData.length > 0) {
                // Category filter buttons
                const categories = [...new Set(plansData.map(p => p.category))];
                html += '<div class="flex gap-2 overflow-x-auto pb-4 mb-6 no-scrollbar">';
                html += '<button onclick="filterDiscoverPlans(\'all\')" class="plan-filter-btn active" data-category="all">All Plans</button>';
                categories.forEach(cat => {
                    html += `<button onclick="filterDiscoverPlans('${cat}')" class="plan-filter-btn" data-category="${cat}">${cat}</button>`;
                });
                html += '</div>';
                
                html += '<div id="plans-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">';
                
                plansData.forEach(plan => {
                    html += `
                        <div class="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all border border-slate-100 cursor-pointer plan-card" 
                             data-category="${plan.category}"
                             onclick='showPlanDetails(${JSON.stringify(plan).replace(/'/g, "&apos;").replace(/"/g, "&quot;")})'>
                            <div class="relative">
                                <img src="${plan.img}" alt="${plan.title}" class="w-full h-48 object-cover" onerror="this.src='https://placehold.co/600x400?text=No+Image'">
                                <span class="absolute top-3 right-3 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-bold">${plan.category}</span>
                            </div>
                            <div class="p-5">
                                <h3 class="font-black text-xl mb-2 text-slate-900">${plan.title}</h3>
                                <p class="text-sm text-slate-600 mb-3">${plan.description}</p>
                                <div class="flex items-center justify-between text-sm mb-3">
                                    <span class="text-slate-500"><i class="fa-regular fa-clock mr-1"></i> ${plan.duration}</span>
                                    <span class="font-bold text-blue-600">${plan.budget}</span>
                                </div>
                                <div class="flex flex-wrap gap-1.5 mb-3">
                                    ${plan.best_for ? plan.best_for.slice(0, 3).map(tag => 
                                        `<span class="bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs font-bold">${tag}</span>`
                                    ).join('') : ''}
                                </div>
                                <div class="text-blue-600 font-bold text-sm">
                                    ${plan.itinerary ? plan.itinerary.length : 0} Stops <i class="fa-solid fa-arrow-right ml-1"></i>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
            } else {
                html += '<div class="text-center py-12 text-slate-500">No curated plans available yet.</div>';
            }
            
            html += '</div>';
            
            container.innerHTML = html;
        }
        
        // Filter curated plans by category
        function filterDiscoverPlans(category) {
            // Update button styles
            document.querySelectorAll('.plan-filter-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.category === category) {
                    btn.classList.add('active');
                }
            });
            
            // Show/hide plans
            document.querySelectorAll('.plan-card').forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }
        
        // Show plan details in modal
        function showPlanDetails(plan) {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black/50 z-[200] flex items-center justify-center p-4 animate-fade-in';
            modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
            
            const itineraryHTML = plan.itinerary ? plan.itinerary.map(step => `
                <div class="flex gap-4 mb-6">
                    <div class="flex-shrink-0 w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg">
                        ${step.step}
                    </div>
                    <div class="flex-grow">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="font-bold text-blue-600">${step.time}</span>
                            <span class="text-slate-400">•</span>
                            <span class="text-slate-600 text-sm">${step.duration}</span>
                            <span class="ml-auto font-bold text-green-600">${step.cost}</span>
                        </div>
                        <h4 class="font-bold text-slate-900 mb-1">${step.activity}</h4>
                        <p class="text-sm text-slate-600 mb-2">${step.notes}</p>
                        <span class="inline-block bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs">${step.type}</span>
                    </div>
                </div>
            `).join('') : '';
            
            modal.innerHTML = `
                <div class="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl" onclick="event.stopPropagation()">
                    <div class="relative">
                        <img src="${plan.img}" alt="${plan.title}" class="w-full h-56 object-cover" onerror="this.src='https://placehold.co/600x400?text=No+Image'">
                        <button onclick="this.closest('.fixed').remove()" 
                                class="absolute top-4 right-4 bg-white/90 backdrop-blur rounded-full w-10 h-10 flex items-center justify-center shadow-lg hover:bg-white">
                            <i class="fa-solid fa-xmark text-xl text-slate-800"></i>
                        </button>
                    </div>
                    <div class="p-6">
                        <div class="flex items-center gap-2 mb-3">
                            <span class="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-bold">${plan.category}</span>
                            <span class="text-slate-500 text-sm">${plan.duration}</span>
                        </div>
                        <h2 class="text-3xl font-black text-slate-900 mb-3">${plan.title}</h2>
                        <p class="text-slate-700 mb-4">${plan.description}</p>
                        
                        ${plan.best_for ? `
                            <div class="flex flex-wrap gap-2 mb-6">
                                ${plan.best_for.map(tag => 
                                    `<span class="bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full text-sm font-bold">${tag}</span>`
                                ).join('')}
                            </div>
                        ` : ''}
                        
                        <div class="bg-green-50 border-2 border-green-200 rounded-xl p-4 mb-6">
                            <div class="flex justify-between items-center">
                                <span class="text-slate-700 font-bold">Total Budget</span>
                                <span class="text-2xl font-black text-green-600">${plan.total_cost}</span>
                            </div>
                        </div>
                        
                        <h3 class="font-black text-2xl mb-6 text-slate-900">Itinerary</h3>
                        ${itineraryHTML}
                        
                        ${plan.tips ? `
                            <div class="mt-6 bg-amber-50 border-l-4 border-amber-500 rounded-r-xl p-5">
                                <div class="flex gap-3">
                                    <i class="fa-solid fa-lightbulb text-amber-600 text-xl mt-1"></i>
                                    <div>
                                        <h4 class="font-bold text-amber-900 mb-2">Pro Tips</h4>
                                        <p class="text-amber-800 leading-relaxed">${plan.tips}</p>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        }
'''
    
    # Add CSS for filter buttons if not already present
    if '.plan-filter-btn' not in html:
        css_addition = '''
        .plan-filter-btn {
            padding: 8px 16px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 700;
            background: white;
            color: #64748b;
            border: 2px solid #e2e8f0;
            transition: all 0.2s;
            white-space: nowrap;
            cursor: pointer;
        }
        .plan-filter-btn.active {
            background: #2563eb;
            color: white;
            border-color: #2563eb;
        }
        .plan-filter-btn:hover:not(.active) {
            border-color: #cbd5e1;
        }
        .animate-fade-in {
            animation: fadeIn 0.2s ease-out;
        }
'''
        html = html.replace('</style>', css_addition + '\n    </style>')
        print("   * Added CSS for plan filter buttons")
    
    # Insert functions before closing </script> tag
    html = re.sub(
        r'(\s*</script>\s*</body>)',
        discover_functions + r'\1',
        html
    )
    
    print("   * Renamed tab to 'Discover'")
    print("   * Added two-section layout (Activities + Curated Plans)")
    print("   * Added plan filtering by category")
    print("   * Added plan detail modal")
    
    # Save
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n>> SUCCESS! Updated HTML saved to {output_html}")
    print(">> Now run: py update_localspot.py")

if __name__ == "__main__":
    update_html_for_discover_tab()
