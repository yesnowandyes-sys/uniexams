# ESAT Taxonomy Reference

Complete module, topic, subtopic, and skill taxonomy from the ESAT specification.
Source: `esat_taxonomy.json` (enrichment pipeline)

## Code System

| Level | Format | Example | Used in |
|-------|--------|---------|---------|
| Module | Single letter | `M1`, `P`, `C`, `B` | Top-level grouping |
| Topic | Code under module | `M2`, `MM1`, `P3`, `B4`, `C4` | `topic_key` column |
| Subtopic | Topic + dot + number | `M2.7`, `P1.2`, `MM1.3` | `content_code` in enrichment |
| Skill | Subtopic + dot + number | `M2.7.1`, `P1.2.3` | `skills_json` column |

### Topic Key Prefixes

| Code Range | Prefix | Module |
|------------|--------|--------|
| M1-M7 | MATHS1 | Mathematics 1 |
| MM1-MM8 | MATHS2 | Mathematics 2 |
| P1-P7 | PHYS | Physics |
| B1-B11 | BIO | Biology |
| C1-C17 | CHEM | Chemistry |

## Module M1: Mathematics 1

### M1: Units

- **M1.1: Use standard units of mass, length, time, money and other measures.**
  - Use standard units of mass, length, time, money and other measures.
  - Use compound units such as speed, rates of pay, unit pricing, density and pressure, including using decimal quantities where appropriate.
- **M1.2: Change freely between related standard units (e.g.**
  - Change freely between related standard units (e.g.
  - time, length, area, volume/capacity, mass) and compound units (e.g.
  - speed, rates of pay, prices, density, pressure) in numerical and algebraic contexts.
  - Changing between standard units The table shows the conversion rates for common measures.

### M2: Number

- **M2.1: Order positive and negative integers, decimals and fractions.**
  - Order positive and negative integers, decimals and fractions.
  - Understand and use the symbols: = , ≠ , < , > , ≤ , ≥
- **M2.2: Apply the four operations (addition, subtraction, multiplication and division) to integers, decimals, simple fractions (proper and improper) and mixed**
  - Apply the four operations (addition, subtraction, multiplication and division) to integers, decimals, simple fractions (proper and improper) and mixed numbers – any of which could be positive and negative.
  - Understand and use place value.
- **M2.3: Use the concepts and vocabulary of prime numbers, factors (divisors), multiples, common factors, common multiples, highest common factor, lowest commo**
  - Use the concepts and vocabulary of prime numbers, factors (divisors), multiples, common factors, common multiples, highest common factor, lowest common multiple, and prime factorisation (including use of product notation and the unique factorisation theorem).
- **M2.4: Recognise and use relationships between operations, including inverse operations.**
  - Recognise and use relationships between operations, including inverse operations.
  - Use cancellation to simplify calculations and expressions.
  - Understand and use the convention for priority of operations, including brackets, powers, roots and reciprocals.
- **M2.5: Apply systematic listing strategies.**
  - Apply systematic listing strategies.
  - (For instance, if there are 𝑚 ways of doing one task and for each of these tasks there are 𝑛 ways of doing another task, then the total number of ways the two tasks can be done in order is 𝑚 × 𝑛 ways.) If there are m ways of doing one task and for each of these, there are n ways of doing another task, then the total number of ways the two tasks can be done in order is m × n ways.
- **M2.6: Use and understand the terms: square, positive and negative square root, cube and cube root.**
  - Use and understand the terms: square, positive and negative square root, cube and cube root.
- **M2.7: Use index laws to simplify numerical expressions, and for multiplication and division of integer, fractional and negative powers.**
  - Use index laws to simplify numerical expressions, and for multiplication and division of integer, fractional and negative powers.
  - Index numbers or powers The power a number is raised to is the index (plural: indices).
  - For example, 2 × 2 × 2 × 2 × 2 = 25 = 32   so 25 is 32 written in index form.
- **M2.8: Interpret, order and calculate with numbers written in standard index form (standard form); numbers are written in standard form as 𝑎 × 10n, where 1 ≤**
  - Interpret, order and calculate with numbers written in standard index form (standard form); numbers are written in standard form as 𝑎 × 10n, where 1 ≤ 𝑎 < 10 and n is an integer.
- **M2.9: Convert between terminating decimals, percentages and fractions.**
  - Convert between terminating decimals, percentages and fractions.
  - Convert between recurring decimals and their corresponding fractions.
- **M2.10: Use fractions, decimals and percentages interchangeably in calculations.**
  - Use fractions, decimals and percentages interchangeably in calculations.
  - Understand equivalent fractions.
  - Use fractions, decimals and percentages interchangeably in calculations Many problems involve numbers being given in different forms.
  - In those situations, you have to choose the most appropriate method of calculation: whether to use fractions, decimals or percentages.
  - When multiplying a decimal by a fraction, either change both into fractions – usually the easier option – or change both into decimals.
  - Equivalent fractions To find fractions equivalent to a given fraction, either multiply numerator and denominator by the same number or divide numerator and denominator by the same number:
- **M2.11: Calculate exactly with fractions, surds and multiples of π.**
  - Calculate exactly with fractions, surds and multiples of π.
  - Simplify surd expressions involving squares, e.g.
  - √12  = √4 × 3  = √4 √3  =  2√3 , and rationalise denominators; for example, candidates could be asked to rationalise expressions such as: √7  , 3 + 2√5   , 2 − √3  , √5 − √2
- **M2.12: Calculate with upper and lower bounds, and use in contextual problems.**
  - Calculate with upper and lower bounds, and use in contextual problems.
  - Finding upper and lower bounds If a number is rounded to a value, 𝑥, then the greatest lower bound is the smallest number which would round up to 𝑥.
  - The least upper bound is the smallest number which would round up to a number bigger than 𝑥.
  - [Instead of referring to greatest lower bound and least upper bounds, we shall just a call them the lower bound and the upper bound or GLB and LUB] If the number were 3.84 correct to 2 decimal places, then: the lower bound would be 3.835   which is the smallest number which would round to 3.84 the upper bound would be 3.845   which is the smallest number which rounds to a number bigger than 3.84.
- **M2.13: Round numbers and measures to an appropriate degree of accuracy, e.g.**
  - Round numbers and measures to an appropriate degree of accuracy, e.g.
  - to a specified number of decimal places or significant figures.
  - Use inequality notation to specify simple error intervals due to truncation or rounding.
  - Rounding numbers to a given number of decimal places (d.p) To round to, for example, 3 d.p.: if the number in the 4th decimal place is 5 or more add 1 to the number in the third decimal place otherwise leave it unchanged.
  - Rounding numbers to a given number of significant figures (sig.
  - figs.) To round to, for example, 3 sig.
  - figs.:   count the three significant figures from left to right starting with the non-zero digit furthest to the left cut off all digits to the right of the third significant figure replacing
- **M2.14: Use approximation to produce estimates of calculations, including expressions involving  π  or surds.**
  - Use approximation to produce estimates of calculations, including expressions involving  π  or surds.
  - Estimating a calculation Estimating a calculation is a useful check on the accuracy of a calculation, particularly to see if the magnitude of an answer is correct.
  - Numbers are approximated, usually to 1 or 2 significant figures to enable simple calculation; for example, 397 000 would be approximated to 400 000.
  - π  is usually approximated to 3 or Surds are usually approximated to the nearest square number.
  - For example, √15.6 ≈  √16 or 4.
  - Estimating a calculation A calculator gives the value of √

### M3: Ratio and proportion

- **M3.1: Understand and use scale factors, scale diagrams and maps.**
  - Understand and use scale factors, scale diagrams and maps.
  - Similar shapes and scale factor If two shapes are mathematically similar, then the lengths of the sides of one shape can be found from the lengths of the corresponding sides of the other shape by multiplying each length by the same number.
  - This number is called the scale factor.
  - In the diagram the three triangles are similar.
  - The first triangle has sides of length x, y and z,  and a and b are constants and are the scale factors.
  - A scale factor can be less than 1.
  - In the diagram a > 1 and b < 1 Scale diagrams
- **M3.2: Express a quantity as a fraction of another, where the fraction is less than 1 or greater than 1. One quantity can be expressed as a fraction of another 𝑥 𝑦 is 𝑥 expressed as a fraction of 𝑦 To express one quantity as a fraction of another, both quantities must be in the same units. This will normally be the smaller of the two units. Expressing one quantity as a fraction of another – fraction less than 1 Express 200 g as a fraction of 1 kg. The quantities are in different units so change 1 kg to 1000**
  - (g) 200 g as a fraction of 1000 g is
- **M3.3: Understand and use ratio notation.**
  - Understand and use ratio notation.
  - Ratio notation If a bag contains x red sweets and y yellow sweets, then the ratio of red sweets to yellow sweets is x : y which can also be written as x to y.
  - Simplifying ratios Both sides of the ratio can be multiplied or divided by the same positive number without changing the ratio.
  - Comparing using ratios To compare quantities as ratios, the units must be the same.
  - Ratio notation
- **M3.4: Divide a given quantity into two (or more) parts in a given part : part ratio.**
  - Divide a given quantity into two (or more) parts in a given part : part ratio.
  - Express the division of a quantity into two parts as a ratio.
  - Dividing in a given ratio To divide a quantity Q in the ratio x ∶ y, first divide Q by x + y to find the value of one part.
  - Multiply the value of one part by x to find the value of x parts and then by y to find the value of y parts.
  - Check that the values of the x parts and the y parts add up to Q.
  - Expressing a division into parts as a ratio To express the division of a quantity into two parts as a ratio, first make sure that both parts are in the same units and then use ratio notation to relate them.
  - Dividing in a given ratio
- **M3.5: Apply ratio to real contexts and problems, such as those involving conversion, comparison, scaling, mixing and concentrations.**
  - Apply ratio to real contexts and problems, such as those involving conversion, comparison, scaling, mixing and concentrations.
  - Express a multiplicative relationship between two quantities as a ratio or a fraction.
  - Ratio can be applied to problems involving:
- **M3.6: Understand and use proportion.**
  - Understand and use proportion.
  - Relate ratios to fractions and to linear functions.
  - Simple proportion If 𝑥 bars of chocolate cost £𝑦 then 1 bar of the same chocolate costs £ 𝑦 𝑥 and 𝑎 identical bars of the same chocolate costs £ 𝑎𝑦 𝑥 Relating ratios to fractions
- **M3.7: Identify and work with fractions in ratio problems.**
  - Identify and work with fractions in ratio problems.
  - Ratios and fractions If the ratio of x : y  is  p : q  then 𝑥 𝑦= 𝑝 𝑞 Example A bag contains y yellow counters, g green counters and r red counters.
- **M3.8: Define percentage as ‘number of parts per hundred’.**
  - Define percentage as ‘number of parts per hundred’.
  - Interpret percentages and percentage changes as a fraction or a decimal, and interpret these multiplicatively.
  - Express one quantity as a percentage of another.
  - Compare two quantities using percentages.
  - Work with percentages greater than 100%.
  - Solve problems involving percentage change, including percentage increase/decrease, original value problems and simple interest calculations.
  - Percentage as parts per hundred Percentage means ‘number of parts per hundred’.
- **M3.9: Understand and use direct and inverse proportion, including algebraic representations.**
  - Understand and use direct and inverse proportion, including algebraic representations.
  - Recognise and interpret graphs that illustrate direct and inverse proportion.
  - Set up, use and interpret equations to solve problems involving direct and inverse proportion (including questions involving integer and fractional powers).
  - Understand that 𝑥 is inversely proportional to 𝑦 is equivalent to 𝑥 is proportional to 𝑦 Note: The sign for ‘is proportional to’ is ∝ Direct proportion If one chocolate bar costs £6 then 6 bars cost £36 and x bars cost £6x.
  - There is no reduction in price per bar for bulk buying.
  - The number of chocolate bars and the total price are in direct proportion, one
- **M3.10: Compare lengths, areas and volumes using ratio notation.**
  - Compare lengths, areas and volumes using ratio notation.
  - Understand and make links to similarity (including trigonometric ratios) and scale factors.
  - Definition of similarity If two shapes are mathematically similar then one shape is an enlargement of the other – they are the same shape, have the same angles in the same order and corresponding sides are in the same ratio.
  - Area ratio and volume ratio from a linear scale factor If two shapes A and B are mathematically similar and the lengths of the sides of B are x times the lengths of the corresponding sides of A, then:
- **M3.11: Set up, solve and interpret the answers in growth and decay problems, including compound interest, and work with general iterative processes.**
  - Set up, solve and interpret the answers in growth and decay problems, including compound interest, and work with general iterative processes.
  - Exponential growth and decay Problems of growth and decay will involve a rate of growth or decay where the quantity is multiplied by the same number in each time period.
  - If the size of the population initially (at time = 0) is q and the size of the population is multiplied by a factor x every hour, then after n hours the size of the population is qxn.
  - For growth x > 1 and for decay 0 < x < 1.
  - If x = 1 the population is static.
  - Examples are bacteria colonies which treble in size every hour or a substance losing half of its radioactivity every 6 hours.

### M4: Algebra

- **M4.1: Understand, use and interpret algebraic notation; for instance: 𝑎𝑏 in place of 𝑎 × 𝑏 ; 3𝑦 in place of 𝑦 + 𝑦 + 𝑦 and 3 × 𝑦 ; 𝑎2  in place of 𝑎 × 𝑎 ; 𝑎3**
  - Understand, use and interpret algebraic notation; for instance: 𝑎𝑏 in place of 𝑎 × 𝑏 ; 3𝑦 in place of 𝑦 + 𝑦 + 𝑦 and 3 × 𝑦 ; 𝑎2  in place of 𝑎 × 𝑎 ; 𝑎3 in place of 𝑎 × 𝑎 × 𝑎 ; 𝑎2 𝑏 in place of 𝑎 × 𝑎 × 𝑏 ; 𝑎/𝑏   in place of 𝑎 ÷ 𝑏.
  - Using letters and numbers in algebra Numbers, letters, and brackets are multiplied or divided together, to make algebraic terms Multiplying a × b can be written as ab without the ‘×’ and any spaces p × q × r = pqr a × a can be written as a2 p × p × p = p3
- **M4.2: Use index laws in algebra for multiplication and division of integer, fractional, and negative powers.**
  - Use index laws in algebra for multiplication and division of integer, fractional, and negative powers.
  - Index notation a5 means a raised to the power 5, where a is the base, and 5 is the power or index (plural indices).
  - a × a × a × a × a = a5
- **M4.3: Substitute numerical values into formulae and expressions, including scientific formulae.**
  - Substitute numerical values into formulae and expressions, including scientific formulae.
  - Understand and use the concepts and vocabulary: expressions, equations, formulae, identities, inequalities, terms and factors.
- **M4.4: Collect like terms, multiply a single term over a bracket, take out common factors, and expand products of two or more binomials.**
  - Collect like terms, multiply a single term over a bracket, take out common factors, and expand products of two or more binomials.
  - Like terms Like terms in algebra are identical apart from the numerical constant multiplier which may or may not be the same.
  - 12x2y4 and −6x2y4 are like terms.
  - 10y2  and 0.75y2 are like terms.
  - 12x2y4 and 12x2y3  are not like terms.
  - 10y2 and 10y are not like terms.
  - Like terms can be collected, they can then be combined by adding and subtracting.
  - Multiplying a single term over a bracket
- **M4.5: Factorise quadratic expressions of the form 𝑥2  + 𝑏𝑥 + 𝑐 , including the difference of two squares. Factorise quadratic expressions of the form 𝑎𝑥2  + 𝑏𝑥 + 𝑐 , including the difference of two squares. Factorising quadratic expressions of the form 𝑥2  + 𝑏𝑥 + 𝑐 Some quadratic expressions of the form 𝑥2  + 𝑏𝑥 + 𝑐  can be expressed as a product of two linear expressions with integer coefficients: (𝑥 + 𝑝)(𝑥 + 𝑞) where 𝑏 = 𝑝 + 𝑞  and 𝑐 = 𝑝𝑞. In other words, p and q are two numbers whose product is c and whose sum is**
  - (b) For example, 𝑥2  + 5𝑥 + 6 = (𝑥 + 3)(𝑥 + 2) Factorising quadratic expressions of the form 𝑥2 − 𝑎2     - the difference of two squares Quadratic expressions of the form 𝑥2 − 𝑎2 are called the difference of two squares and can be factorised as   (𝑥+ 𝑎)(𝑥− 𝑎).
- **M4.6: Simplify expressions involving sums, products and powers, including the laws of indices.**
  - Simplify expressions involving sums, products and powers, including the laws of indices.
  - Simplify rational expressions by cancelling, or factorising and cancelling.
  - Use the four rules on algebraic rational expressions.
  - Simplifying expressions involving sums, products and powers Expressions can be simplified in a number of ways.
- **M4.7: Rearrange formulae to change the subject.**
  - Rearrange formulae to change the subject.
  - Changing the subject of the formula means expressing one variable in the formula in terms of the other variables.
  - To do this the formula must be rearranged according to the rules of arithmetic and algebra in order to isolate the new subject:
- **M4.8: Understand the difference between an equation and an identity.**
  - Understand the difference between an equation and an identity.
  - Argue mathematically to show that algebraic expressions are equivalent.
- **M4.9: Work with coordinates in all four quadrants.**
  - Work with coordinates in all four quadrants.
  - The coordinate axes The coordinate axes 𝑥 and 𝑦 are a way of locating points in the plane.
  - They cross at the origin.
  - The axes divide the plane into 4 quadrants as shown in the diagram.
  - The 𝑥-axis is usually horizontal, positive numbers to the right of the origin and negative to the left.
  - The 𝑦-axis is usually vertical, positive numbers above the origin and negative numbers below.
  - The coordinates of a point are given as 2 numbers in a bracket, separated by a comma with the 𝑥 coordinate first.
  - A is the point (4,2), B is (−4,2), C is (−2,−4) and D is (2,−4).
- **M4.10: Identify and interpret gradients and intercepts of linear functions ( 𝑦 = 𝑚𝑥 + 𝑐 ) graphically and algebraically.**
  - Identify and interpret gradients and intercepts of linear functions ( 𝑦 = 𝑚𝑥 + 𝑐 ) graphically and algebraically.
  - Identify pairs of parallel lines and identify pairs of perpendicular lines, including the relationships between gradients.
  - Find the equation of the line through two given points, or through one point with a given gradient.
  - Equation of a straight line The equation of a straight line can be written in the form 𝑦 = 𝑚𝑥 + 𝑐  where 𝑚 is the gradient of the line and 𝑐 is the intercept with the 𝑦–axis.
  - Parallel lines Parallel lines have the same gradient.
- **M4.11: Identify and interpret roots, intercepts and turning points of quadratic functions graphically.**
  - Identify and interpret roots, intercepts and turning points of quadratic functions graphically.
  - Deduce roots algebraically, and turning points by completing the square.
  - A quadratic function of a variable 𝑥 is a function of the form 𝑓(𝑥) = 𝑎𝑥2  + 𝑏𝑥 + 𝑐  where 𝑎, 𝑏, and 𝑐 are constants.
  - The graph of 𝑓(𝑥) is a parabola and its orientation depends on the value of 𝑎.
- **M4.12: Recognise, sketch and interpret graphs of**
  - (a) linear functions
  - (b) quadratic functions
  - (c) simple cubic functions
  - (d) the reciprocal function: 𝑦= 𝑥 with 𝑥 ≠ 0
  - (e) the exponential function: 𝑦 = 𝑘𝑥 for positive values of k
  - (f) trigonometric functions (with arguments in degrees): 𝑦 = 𝑠𝑖𝑛 𝑥, 𝑦 = 𝑐𝑜𝑠 𝑥, 𝑦 = 𝑡𝑎𝑛 𝑥 for angles of any size Recognise and sketch graphs of:
- **M4.13: Interpret graphs (including reciprocal graphs and exponential graphs) and graphs of non-standard functions in real contexts to find approximate soluti**
  - Interpret graphs (including reciprocal graphs and exponential graphs) and graphs of non-standard functions in real contexts to find approximate solutions to problems, such as simple kinematic problems involving distance, speed and acceleration.
  - Straight line graphs Straight line graphs that pass through the origin represent simple proportional relationships, e.g.
  - cost of items with no reduction for bulk buying, distance travelled at constant speed, exchange rates with no administration fee.
  - If the line does not go through the origin, then it suggests an initial charge then a proportional relationship, e.g.
  - the initial cost of a mobile phone plus a fixed monthly fee.
  - Reciprocal graphs
- **M4.14: Calculate or estimate gradients of graphs and areas under graphs (including quadratic and other non- linear graphs), and interpret results in cases su**
  - Calculate or estimate gradients of graphs and areas under graphs (including quadratic and other non- linear graphs), and interpret results in cases such as distance–time graphs, speed–time graphs and graphs in financial contexts.
  - Gradient of straight-line graphs The gradient of the straight line 𝑦 = 𝑚𝑥 + 𝑐  is 𝑚.
  - If (𝑎,𝑏) and (𝑐,𝑑) are two points on a straight line, the gradient of the line is 𝑑−𝑏 𝑐−𝑎 Gradient of curves The gradient of a curve at a point is equal to the gradient of the tangent to the curve at that point.
- **M4.15: Set up and solve, both algebraically and graphically, simple equations including simultaneous equations involving two unknowns; this may include one l**
  - Set up and solve, both algebraically and graphically, simple equations including simultaneous equations involving two unknowns; this may include one linear and one quadratic equation.
  - Solve two simultaneous equations in two variables (linear/linear or linear/quadratic) algebraically.
  - Find approximate solutions using a graph.
  - Translate simple situations or procedures into algebraic expressions or formulae; for example, derive an equation (or two simultaneous equations), solve the equation(s) and interpret the solution.
  - In solving an equation, the aim is to isolate the unknown quantity and find its value.
- **M4.16: Solve quadratic equations (including those that require rearrangement) algebraically by factorising, by completing the square, and by using the quadra**
  - Solve quadratic equations (including those that require rearrangement) algebraically by factorising, by completing the square, and by using the quadratic formula.
- **M4.17: Solve linear inequalities in one or two variables.**
  - Solve linear inequalities in one or two variables.
  - Represent the solution set on a number line, or on a graph, or in words.
  - Symbols and labelling conventions Single variable < Less than (looks like an L for less) x < 4 defines points on a number line such that x can take any value less than but not including 4.
- **M4.18: Generate terms of a sequence using term-to-term or position-to-term rules.**
  - Generate terms of a sequence using term-to-term or position-to-term rules.
  - A sequence is a list of terms together with a rule for generating them.
  - Sequences can be generated using a term-to-term rule or position-to-term rule.
  - A term-to-term rule indicates how to move from one term in the sequence to the next term in the sequence.
  - A position-to-term rule indicates how to move from the position in the sequence to the term in the sequence.
  - For example, how to find the term in position 20 of the sequence.
  - Examples of a term-to-term rule Sequences may be described by giving the first term and the term-to-term rule.
  - For example, the sequence with first term 3 and term-to-term rule +4 is 3, 7, 11, 15, 19, … as you are adding 4 each time
- **M4.19: Deduce expressions to calculate the 𝑛th term of linear or quadratic sequences.**
  - Deduce expressions to calculate the 𝑛th term of linear or quadratic sequences.
  - If we know a list of terms in a sequence, we can find the nth term which is also the position-to-term rule for working out any term in the sequence.
  - For a linear sequence, the terms increase by the same amount each time.
  - We say there is a constant difference between the terms.
  - For a quadratic sequence, the terms are generated using an nth term which is in the form an2 + bn + c where either b or c could be 0.
  - The nth term for the linear sequence 1, 3, 5, 7, … is 2n–1 The nth term for the quadratic sequence 1, 7, 17, 31, … is 2n2–1 Finding an nth term for a linear sequence

### M5: Geometry

- **M5.1: Use conventional terms and notation: points, lines, line segments, vertices, edges, planes, parallel lines, perpendicular lines, right angles, subtend**
  - Use conventional terms and notation: points, lines, line segments, vertices, edges, planes, parallel lines, perpendicular lines, right angles, subtended angles, polygons, regular polygons and polygons with reflection and/or rotational symmetries.
- **M5.2: Recall and use the properties of angles at a point, angles on a straight line, perpendicular lines and opposite angles at a vertex.**
  - Recall and use the properties of angles at a point, angles on a straight line, perpendicular lines and opposite angles at a vertex.
  - Understand and use the angle properties of parallel lines, intersecting lines, triangles and quadrilaterals.
  - Calculate and use the sum of the interior angles, and the sum of the exterior angles, of polygons.
  - Properties of angles around a point, angles on a straight line, perpendicular lines and opposite angles at a vertex The sum of the angles around a point is 360° (a + b + c + d = 360°) The sum of the angles at a point on one side of a straight line is 180° (a + b = b + c = c + d = d + a = 180°) Perpendicular lines are at right angles (90°) to each other.
  - Opposite angles at a vertex are equal (a = c  and  b = d)
- **M5.3: Derive and apply the properties and definitions of special types of quadrilaterals, including square, rectangle, parallelogram, trapezium, kite and rh**
  - Derive and apply the properties and definitions of special types of quadrilaterals, including square, rectangle, parallelogram, trapezium, kite and rhombus.
  - Derive and apply the properties and definitions of various types of triangle and other plane figures using appropriate language.
  - Labelling In the triangle ABC, the capital letters A, B and C refer to the angles at the vertices, and the small letters a, b and c refer to the sides opposite those angles.
  - Quadrilaterals, and other plane figures, should be labelled consistently either clockwise or anti-clockwise.
  - It does not matter which vertex you start labelling from.
- **M5.4: Understand and use the basic congruence criteria for triangles (SSS, SAS, ASA, RHS).**
  - Understand and use the basic congruence criteria for triangles (SSS, SAS, ASA, RHS).
  - Definition Two shapes are congruent if they are identical in shape and size.
  - SSS (side, side, side): Two triangles A and B are congruent if the three sides of A are the same lengths as the three sides of B.
- **M5.5: Apply angle facts, triangle congruence, similarity, and properties of quadrilaterals to results about angles and sides.**
  - Apply angle facts, triangle congruence, similarity, and properties of quadrilaterals to results about angles and sides.
  - You will need to recall the information from sections M5.1 to M5.4.
  - Properties of triangles In the isosceles triangle ABC, AB = AC and angle BAC = 50°.
  - Another isosceles triangle CAD is drawn in the same plane as triangle ABC, as in the diagram, with angle CAD = 18° What is the size of angle DBC?
  - Mark all equal lengths onto the diagram: AB = AC = AD This shows that triangle ABD is isosceles.
  - Join B and D to form the triangle DBC, which contains the angle DBC.
- **M5.6: Identify, describe and construct congruent and similar shapes, including on coordinate axes, by considering rotation, reflection, translation and enla**
  - Identify, describe and construct congruent and similar shapes, including on coordinate axes, by considering rotation, reflection, translation and enlargement (including fractional and negative scale factors).
  - Describe the changes and invariance achieved by combinations of rotations, reflections and translations.
  - Describe translations as 2-dimensional vectors.
  - Note When we write about transformations, the original shape is referred to as the object and the transformed shape as the image.
  - Points which stay in the same place under the transformation are called invariant points.
  - Rotation
- **M5.7: Know and use the formula for Pythagoras’ theorem: a2 + b2 = c2 Use Pythagoras’ theorem in both 2 and 3 dimensions.**
  - Know and use the formula for Pythagoras’ theorem: a2 + b2 = c2 Use Pythagoras’ theorem in both 2 and 3 dimensions.
  - Pythagoras’ theorem in 2 dimensions Pythagoras’ theorem applies to right-angled triangles, and it says: 𝐚𝟐+ 𝐛𝟐= 𝐜𝟐
- **M5.8: Identify and use conventional circle terms: centre, radius, chord, diameter, circumference, tangent, arc, sector and segment (including the use of the**
  - Identify and use conventional circle terms: centre, radius, chord, diameter, circumference, tangent, arc, sector and segment (including the use of the terms minor and major for arcs, sectors and segments).
  - Diagram 1 The circumference of a circle (the black outline on the diagram) is the distance around the outside of the circle.
  - The centre of a circle (O on the diagram) is the point which is the same distance from every point on the circumference.
  - It is the point where the lines of symmetry meet.
  - A line segment from the centre to the circumference of the circle is the radius of the circle.
  - The term radius is also used to refer to the length of this line.
  - The diameter of a circle is a line segment that passes through the centre of the circle and has endpoints
- **M5.9: Apply the standard circle theorems concerning angles, radii, tangents and chords, and use them to prove related results**
  - (a) angle subtended at the centre is twice the angle subtended at the circumference
  - (b) angle in a semicircle is 90°
  - (c) angles in the same segment are equal
  - (d) angle between a tangent and a chord (alternate segment theorem)
  - (e) angle between a radius and a tangent is 90°
  - (f) properties of cyclic quadrilaterals The angle subtended at the centre of a circle by a chord In the diagrams, angle ACB is the angle subtended at the point C by the arc AB or the points A and B or
- **M5.10: Solve geometrical problems on 2-dimensional coordinate axes.**
  - Solve geometrical problems on 2-dimensional coordinate axes.
  - Distance between two points The distance between two points on coordinate axes can be found using Pythagoras’ theorem.
  - If the points are A(a,b) and C(c,d), and B is the point where a vertical line from C meets a horizontal line from A then, using Pythagoras’ theorem: AC2 = AB2 + BC2 or AC2 = (c − a)2 + (d − b)2 = (d − b)2 + (c − a)2 (distance between two points)2 = (difference in y coordinates)2 + (difference in x coordinates)2 Finding midpoints The midpoint of two points A(𝑎,𝑏) and C(𝑐,𝑑) is  ( 𝑎+𝑐
- **M5.11: Know the terminology faces, surfaces, edges and vertices when applied to cubes, cuboids, prisms, cylinders, pyramids, cones, spheres and hemispheres.**
  - Know the terminology faces, surfaces, edges and vertices when applied to cubes, cuboids, prisms, cylinders, pyramids, cones, spheres and hemispheres.
  - Note These definitions are simply that: ideas defined by some individual, group or organisation.
  - Different textbooks may define things in different ways so, for example, in some definitions a cylinder is a prism, in others it is not.
  - In some books a face has to have straight-line edges, in others a face can be circular.
  - Examination questions state what is meant if there is any doubt, and they do not ask for definitions that are not universally agreed.
  - A face of a 3-dimensional figure is usually defined as a flat surface of a polyhedron, so a cube has 6 faces but a sphere has none.
  - Most definitions require a face to be a polygon, so cylinders and hemispheres
- **M5.12: Interpret plans and elevations of 3-dimensional shapes.**
  - Interpret plans and elevations of 3-dimensional shapes.
  - The plan of a 3-dimensional shape is the view from above looking down onto the object.
  - The plan of a square based right pyramid would look like this: When you are drawing a plan and front and side elevations, you normally label the front and side onto the plan.
  - The plan gives us some idea of what the shape looks like, but tells us nothing about its height or whether or not it is standing on another shape.
  - The front elevation is what you would see if you were standing in front of the object looking at it directly.
  - You are normally told which is the front.
  - The side elevation is what you would see if you were looking directly at the side of the object.
- **M5.13: Use and interpret maps and scale drawings.**
  - Use and interpret maps and scale drawings.
  - Understand and use three-figure bearings.
  - Maps and scale drawings A scale drawing is an enlargement of the original drawing, usually with a fractional scale factor.
  - If a circle on the original drawing has radius 2 m, and the same circle on the scale drawing has a radius of 10 cm, then the scale factor of the enlargement is 2 m 10 cm = 200 cm 10 cm =
- **M5.14: Know and apply formulae to calculate**
  - (a) the area of triangles, parallelograms, trapezia
  - (b) the volume of cuboids and other right prisms. Area of a triangle The area of a triangle is 2 (base × height) The height must be measured perpendicular to the base. Area of a parallelogram The area of a parallelogram is base × height The height is the perpendicular distance between the base and the s
- **M5.15: Know the formulae**
  - (a) circumference of a circle = 2πr = πd
  - (b) area of a circle = πr2
  - (c) volume of a right circular cylinder = πr2h Formulae relating to spheres, pyramids and cones will be given if needed.
- **M5.16: Calculate arc lengths, angles and areas of sectors of circles.**
  - Calculate arc lengths, angles and areas of sectors of circles.
  - A sector of a circle centre O is an area of the circle bounded by 2 radii and an arc of the circle.
  - 2 radii divide a circle into 2 sectors, the major sector and the minor sector.
  - Sector angle The angle between the 2 radii is called the sector angle.
  - Sector area If the sector angle is 𝑥° then the area of the sector is 𝑥 360 × πr2 Arc length
- **M5.17: Apply the concepts of congruence and similarity in simple figures, including the relationships between lengths, areas and volumes.**
  - Apply the concepts of congruence and similarity in simple figures, including the relationships between lengths, areas and volumes.
  - Congruent figures are identical in shape and size – all corresponding lengths and angles are equal.
  - Similar figures are identical in shape, but one figure is an enlargement of the other.
  - All corresponding angles are the same, and corresponding lengths are in the same ratio.
  - All equilateral triangles are similar as are all spheres and all cubes.
  - Length, area and volume If a shape, X, is enlarged with scale factor n to give a similar figure, Y, then the area of Y is n2 times the area of X and the volume of Y is n3 times the volume of X.
  - Congruent figures
- **M5.18: Know and use the trigonometric ratios: Apply these to find angles and lengths in right-angled triangles and, where possible, general triangles in 2- a**
  - Know and use the trigonometric ratios: Apply these to find angles and lengths in right-angled triangles and, where possible, general triangles in 2- and 3dimensional figures.
  - Know the exact values of sin 𝜃 and cos 𝜃 for 𝜃 = 0°, 30°, 45°, 60°, 90°.
  - Know the exact values of tan 𝜃  for θ = 0°, 30°, 45°, 60°.
  - Candidates are not expected to recall or use the sine or cosine rules.
  - Note You need to know the exact values of sin 𝜃, cos 𝜃  and tan 𝜃  for 𝜃 = 0°, 30°, 45° or 60° and of sin 90° and cos 90° either by learning them or learning how to derive them.
  - Sine, cosine and tangent
- **M5.19: Apply addition and subtraction of vectors, multiplication of vectors by a scalar, and diagrammatic and column representations of vectors.**
  - Apply addition and subtraction of vectors, multiplication of vectors by a scalar, and diagrammatic and column representations of vectors.
  - Use vectors to construct geometric arguments and proofs.
  - A vector is a way of describing how to move from one point to another.
  - Vectors describe both direction and size.

### M6: Statistics

- **M6.1: Interpret and construct tables, charts and diagrams, including**
  - (a) two-way tables, frequency tables, bar charts, pie charts and pictograms for categorical data
  - (b) vertical line charts for ungrouped discrete numerical data
  - (c) tables and line graphs for time series data Know the appropriate use of each of these representations. Two-way tables for categorical data A two-way table has both rows and columns forming cells. Each cell contains information relating to the row and column that it belongs to. For example: 20 pupils
- **M6.2: Interpret and construct diagrams for grouped discrete data and continuous data**
  - (a) histograms with equal and unequal class intervals
  - (b) cumulative frequency graphs Know the appropriate use of each of these diagrams. Understand and use the term frequency density. Discrete and continuous data Discrete data is data which can only take certain fixed values. For example, the number of pupils in a class is discrete as it has to be an inte
- **M6.3: Calculate the mean, mode, median and range for ungrouped data.**
  - Calculate the mean, mode, median and range for ungrouped data.
  - Find the modal class; calculate estimates of the range, mean and median for grouped data, and understand why these are estimates.
  - Describe a population using statistics.
  - Make simple comparisons.
  - Compare data sets using like-for-like summary values.
  - Understand the advantages and disadvantages of summary values.
  - Calculate estimates of mean, median, mode, range, quartiles and interquartile range from graphical representation of grouped data.
  - Use the median and interquartile range to compare distributions.
- **M6.4: Use and interpret scatter graphs of bivariate data.**
  - Use and interpret scatter graphs of bivariate data.
  - Recognise correlation, and know that it does not indicate causation.
  - Draw estimated lines of best fit.
  - Interpolate and extrapolate apparent trends whilst knowing the dangers of so doing.

### M7: Probability

- **M7.1: Analyse the frequency of outcomes of probability experiments using tables and frequency trees.**
  - Analyse the frequency of outcomes of probability experiments using tables and frequency trees.
  - The outcomes of probability experiments can be recorded and analysed using tables and frequency trees Matthew has a spinner.
  - The spinner has only a red section, a blue section and a yellow section.
  - Matthew thinks that the spinner may be biased.
  - He spins the spinner 50 times and records the colour that the spinner lands on.
  - The table below shows the outcomes of these 50 spins.
  - Colour Red Blue Yellow
- **M7.2: Apply ideas of randomness, fairness and equally likely events to calculate expected outcomes of multiple future experiments.**
  - Apply ideas of randomness, fairness and equally likely events to calculate expected outcomes of multiple future experiments.
  - Understand that if an experiment is repeated, the outcome may be different.
  - In probability, the sample space is the set of all possible outcomes of an experiment.
  - For example, if the aim of the experiment was to toss a coin twice and record the result, then the sample space could be written as {HH, HT, TH, TT}.
  - An event is a subset of the sample space relating to an experiment.
  - For example, when tossing a coin twice and recording the result, we could have an event ‘one head is obtained’.
  - A fair die is one where there is an equally likely chance of landing on each of the faces.
  - A fair spinner is one where there is an equally likely chance of spinning each of the possible outcomes.
- **M7.3: Relate relative expected frequencies to theoretical probability, using appropriate language and the ‘0 to 1’ probability scale.**
  - Relate relative expected frequencies to theoretical probability, using appropriate language and the ‘0 to 1’ probability scale.
  - The relative expected frequency can be used to calculate the theoretical probability of an event.
  - 𝑝𝑟𝑜𝑏𝑎𝑏𝑖𝑙𝑖𝑡𝑦= 𝑛𝑢𝑚𝑏𝑒𝑟 𝑜𝑓 𝑓𝑎𝑣𝑜𝑢𝑟𝑎𝑏𝑙𝑒 𝑜𝑢𝑡𝑐𝑜𝑚𝑒𝑠 𝑛𝑢𝑚𝑏𝑒𝑟 𝑜𝑓 𝑝𝑜𝑠𝑠𝑖𝑏𝑙𝑒 𝑜𝑢𝑡𝑐𝑜𝑚𝑒𝑠 Probabilities may be given as fractions, decimals or percentages.
  - Probabilities can be shown on a probability scale from 0 to 1 (or 0% to 100%).
  - Rolling a fair six-sided die A fair six-sided die is rolled.
- **M7.4: Apply the property that the probabilities of an exhaustive set of outcomes sum to one.**
  - Apply the property that the probabilities of an exhaustive set of outcomes sum to one.
  - Apply the property that the probabilities of an exhaustive set of mutually exclusive events sum to one.
  - A set of events is said to be exhaustive if at least one of the events must occur.
  - Events are said to be mutually exclusive if no more than one of the events can occur at any time.
  - It is possible for a set of events to be both exhaustive and mutually exclusive.
  - For example, if a fair six- sided die is rolled, the two events ‘land on an even number’ and ‘land on an odd number’ are both exhaustive (as at least one of the events must occur) and mutually exclusive (as the die cannot land on an odd number and an even number simultaneously).
  - The probabilities of an exhaustive set of mutually exclusive events sum to one.
  - We can use this to find unknown probabilities.
- **M7.5: Enumerate sets and combinations of sets systematically, using tables, grids, Venn diagrams and tree diagrams.**
  - Enumerate sets and combinations of sets systematically, using tables, grids, Venn diagrams and tree diagrams.
  - Candidates are not expected to know formal set theory notation.
  - In probability questions it is often important to be able to list the possible outcomes of an experiment systematically and to organise information using tables, grids, Venn diagrams and tree diagrams to answer questions.
  - Listing sets For example, the set of vowels is {a, e, i, o, u} and the set containing the first 10 prime numbers is {2, 3, 5, 7, 11, 13, 17, 19, 23, 29}.
  - Listing combinations of sets Let A be the set containing the first 10 prime numbers.
- **M7.6: Construct theoretical possibility spaces for single and combined experiments with equally likely outcomes, and use these to calculate theoretical prob**
  - Construct theoretical possibility spaces for single and combined experiments with equally likely outcomes, and use these to calculate theoretical probabilities.
  - Possibility spaces (or sample spaces) are used to represent the different possible outcomes for probability experiments with equally likely outcomes.
  - This can then be used to work out the theoretical probability of events occurring.
  - These can be used for single experiments or combined experiments.
  - For example, the possible outcomes of flipping a coin are heads or tails.
  - These are equally likely outcomes (provided the coin is fair) and so the probability of obtaining a head on a single flip of a fair coin is 2.
  - The probability of obtaining a tail on a single flip of a fair coin is also
- **M7.7: Know when to add or multiply two probabilities, and understand conditional probability. Calculate and interpret conditional probabilities through representation using expected frequencies with two-way tables, tree diagrams and Venn diagrams. Understand the use of tree diagrams to represent outcomes of combined events**
  - (a) when the probabilities are independent of the previous outcome
  - (b) when the probabilities are dependent on the previous outcome. Addition of probabilities Events are said to be mutually exclusive if no more than one of the events can occur at any time. When two events, A and B, are mutually exclusive, the probability that A or B will occur is the sum of the probabi


## Module M2: Mathematics 2

### MM1: Algebra and functions

- **MM1.1: Laws of indices for all rational exponents.**
  - Laws of indices for all rational exponents.
  - Indices [or powers, or exponents, if you prefer] are really a mathematician’s method for writing out certain ways of combining numbers without using vast quantities of ink.1 They are a good example of what a well-chosen notation can do.
  - A well-chosen notation aids thinking and makes calculations and manipulations easier than they might otherwise be.
  - For the TMUA/ESAT you are expected to know all the basic rules of indices – both what the notation means and how to deal with the notation.
  - In this section, we will introduce the basic rules we expect you to know along with some informal notes to help you start to think about how the ideas fit together.
  - We start with the very basic idea of an index for a number 𝑎 multiplied by itself a total
- **MM1.2: Use and manipulation of surds.**
  - Use and manipulation of surds.
  - Simplifying expressions that contain surds, including rationalising the denominator.
- **MM1.3: Quadratic functions and their graphs; the discriminant of a quadratic function; completing the square; solution of quadratic equations.**
  - Quadratic functions and their graphs; the discriminant of a quadratic function; completing the square; solution of quadratic equations.
  - Quadratics are essentially functions that are written in the form 𝑎𝑥2 + 𝑏𝑥+ 𝑐   where 𝑎≠0.
  - The term “quadratic” can mean the function, or the graph, or the expression etc.
  - – it is generally a loose term for all things related to the function.
  - In this section we will look at the quadratics both algebraically and graphically.
  - It will help if you read this section in conjunction with the one on “graph shifting” below and also have some graphing software to hand [e.g., DESMOS GRAPHING ].
  - Why is there so much talk about quadratics in GCSE and A level mathematics?
  - The simple answer is that they are both simple to deal with and have lots of interesting
- **MM1.4: Simultaneous equations: analytical solution by substitution, e.g.**
  - Simultaneous equations: analytical solution by substitution, e.g.
  - of one linear and one quadratic equation.
  - In this section, we will look at simultaneous equations.
  - We will look at what simultaneous equations are and then we will investigate how we can solve them.
  - After that, we will look at how the solutions to simultaneous equations fit with the corresponding graphs of the equations.
  - Let’s start by stepping back and exploring how we might think about equations and their graphs in general terms.
  - We start by considering the simple [linear] equation 𝑦= 𝑥+ 2 where 𝑥 is taken from the real numbers.
  - This equation is really a quick way of writing out a [very large] set of
- **MM1.5: Solution of linear and quadratic inequalities.**
  - Solution of linear and quadratic inequalities.
  - The most important things to be aware of when dealing with inequalities is that they do NOT behave quite the same way as equations with equal signs.
  - With inequalities you can add and subtract on both sides as much as you want, but you cannot multiply and divide both sides [or raise both sides to an even power, or apply certain functions to both sides] without first checking that what you are multiplying or dividing by is positive and/or preserves the inequality:
- **MM1.6: Algebraic manipulation of polynomials, including**
  - (a) expanding brackets and collecting like terms
  - (b) factorisation and simple algebraic division (by a linear polynomial, including those of the form a   + b, and by quadratics, including those of the form 𝑎𝑥2 + 𝑏𝑥+ 𝑐)
  - (c) use of the Factor Theorem and the Remainder Theorem In the TMUA/ESAT we expect you to be able to multiply our brackets and collect like terms; and recall collecting ”like terms” means collecting all the constants together, and separately collecting all the 𝑥 terms together, and separately the 𝑥2 ter
- **MM1.7: Qualitative understanding that a function is a many-to-one (or sometimes just a one- to-one) mapping.**
  - Qualitative understanding that a function is a many-to-one (or sometimes just a one- to-one) mapping.
  - Familiarity with the properties of common functions, including  𝑓(𝑥) = √𝑥  (which always means the ‘positive square root’) and  𝑓(𝑥) = |𝑥| Let’s start exploring what is meant by a “function”.
  - In simple terms a function is a mapping [or, better, it is a rule] from a set of input values to a set of output values.
  - Not all algebraic expression are functions and, in this section, we will clarify what special features make something a function.
  - First, let’s look at input and output values.
  - We will be a little loose on notation here26 and so we will use 𝑓(𝑥) to denote an algebraic expression and we will usually combine

### MM2: Sequences and series

- **MM2.1: Sequences, including those given by a formula for the 𝑛th term and those generated by a simple recurrence relation of the form 𝑥𝑛+1 = 𝑓(𝑥𝑛) For this M**
  - Sequences, including those given by a formula for the 𝑛th term and those generated by a simple recurrence relation of the form 𝑥𝑛+1 = 𝑓(𝑥𝑛) For this MM2 section, there are three terms that you should know: series, sequence and progression.
  - A sequence is an ordered list of numbers [often going on forever]; a series is a sum of a sequence; and a progression is just a general term that sits somewhere in between series and sequence.
  - In the TMUA/ESAT we tend to use the term “progression” as a “catch-all” term because it is more neutral and helps us word question in way that makes them easier to understand.32 We expect you to be able to write out sequences of numbers given simple rules and to spot patterns in these sequences and then use the patterns to make further
- **MM2.2: Arithmetic series, including the formula for the sum of the first n natural numbers.**
  - Arithmetic series, including the formula for the sum of the first n natural numbers.
  - In the TMUA/ESAT we expect you to know what an arithmetic series [and sequence] is and recognise one when it appears.
  - We often refer to these as Arithmetic Progressions [APs] in the TMUA.
  - You should also know and understand [i.e., be able to derive35] the standard formulae and terminology: first term = 𝑎 common difference = 𝑑 (nth term )  𝑢𝑛= 𝑎+ (𝑛−1)𝑑 (sum to n terms) Sn = 𝑛
- **MM2.3: The sum of a finite geometric series.**
  - The sum of a finite geometric series.
  - The sum to infinity of a convergent geometric series, including the use of |𝑟| < 1 In the TMUA/ESAT we expect you to know what a geometric series [and sequence] is and recognise one when it appears.
  - We often refer to these as Geometric Progressions [GPs] in the TMUA.
  - You should also know and understand the standard formulae and terminology: first term = 𝑎  [sometimes this is written as 𝑎𝑟0  to fit in with the formula for  𝑢𝑛] common ratio = 𝑟 (nth term )  𝑢𝑛= 𝑎𝑟𝑛−1 sum to n terms Sn = 𝑎(1 −𝑟𝑛)
- **MM2.4: Binomial expansion of  (1 + 𝑥)𝑛  for positive integer n, and for expressions of the form (𝑎+ 𝑓(𝑥)) 𝑛  for positive integer n and simple 𝑓(𝑥).**
  - Binomial expansion of  (1 + 𝑥)𝑛  for positive integer n, and for expressions of the form (𝑎+ 𝑓(𝑥)) 𝑛  for positive integer n and simple 𝑓(𝑥).
  - The notations 𝑛!
  - and (𝑛 𝑟) .
  - The binomial theorem is quite rich mathematically and there are lots of different ways we can approach it.
  - For examinations, the best way is usually just to know the formulae and their quirks; but we do not recommend that you ever learn your mathematics in a way that sidesteps understanding.
  - Here we will start by telling you what you need to know about the binomial expansion for the TMUA/ESAT and give you a few tips; then

### MM3: Coordinate geometry in the (x, y) plane

- **MM3.1: Equation of a straight line, including 𝑦−𝑦1 = 𝑚(𝑥−𝑥1) 𝑎𝑥+ 𝑏𝑦+ 𝑐= 0 Conditions for two straight lines to be parallel or perpendicular to each other.**
  - Equation of a straight line, including 𝑦−𝑦1 = 𝑚(𝑥−𝑥1) 𝑎𝑥+ 𝑏𝑦+ 𝑐= 0 Conditions for two straight lines to be parallel or perpendicular to each other.
  - Finding equations of straight lines given information in various forms.
  - The specification here is self-explanatory as to what you need to know about straight lines.
  - You should be comfortable dealing both algebraically and geometrically [i.e., graphically] with straight lines.
  - In this section we will briefly explore most of the main ideas we expect you to know and add a few things to think about.
  - Let’s start with the classic 𝑦= 𝑚𝑥+ 𝑐  and remind ourselves of what the 𝑚 and the 𝑐
- **MM3.2: Coordinate geometry of the circle: using the equation of a circle in the forms (𝑥−𝑎)2 + (𝑦−𝑏)2 = 𝑟2 𝑥2 + 𝑦2 + 𝑐𝑥+ 𝑑𝑦+ 𝑒= 0 Imagine drawing a circle of**
  - Coordinate geometry of the circle: using the equation of a circle in the forms (𝑥−𝑎)2 + (𝑦−𝑏)2 = 𝑟2 𝑥2 + 𝑦2 + 𝑐𝑥+ 𝑑𝑦+ 𝑒= 0 Imagine drawing a circle of radius 1 on the 𝑥𝑦-plane with its centre at the origin and a radius of 1.
  - What can we say about all the points that sit on this circle?
  - They must all be a distance of 1 from the origin.
  - We can use Pythagoras’ theorem to express this idea in algebra [see the diagram] and when we do so we get the equation of a basic circle:  𝑥2 + 𝑦2 = 12.
  - Any (𝑥, 𝑦) satisfying this equation is on the circle and any (𝑥, 𝑦) not satisfying this equation is not on the circle.43
- **MM3.3: Use of the following circle properties: The perpendicular from the centre to a chord bisects the chord; The tangent at any point on a circle is perpen**
  - Use of the following circle properties: The perpendicular from the centre to a chord bisects the chord; The tangent at any point on a circle is perpendicular to the radius at that point; The angle subtended by an arc at the centre of a circle is twice the angle subtended by the arc at any point on the circumference; The angle in a semicircle is a right angle; Angles in the same segment are equal; The opposite angles in a cyclic quadrilateral add to 180°; The angle between the tangent and chord at the point of contact is equal to the angle in the alternate segment.

### MM4: Trigonometry

- **MM4.1: The sine and cosine rules, and the area of a triangle in the form 2 𝑎𝑏sin C.**
  - The sine and cosine rules, and the area of a triangle in the form 2 𝑎𝑏sin C.
  - The sine rule includes an understanding of the ‘ambiguous’ case (angle-side-side).
  - Problems might be set in 2 or 3 dimensions.
  - We will start this section by looking at the area of a triangle and then explore the sine rule and the cosine rule.
  - A quick note on labelling.
  - We tend to label polygons anticlockwise [not always though – and in this section we have varied the labels we have used on triangles in each diagram to keep you on your toes!].
  - For triangles we label corners [and usually angles in the respective corners] with capital letters, and the sides opposite corners with
- **MM4.2: Radian measure, including use for arc length and area of sector and segment.**
  - Radian measure, including use for arc length and area of sector and segment.
  - Usually, the first method for measuring angles that you will encounter is to use degrees.
  - And, as you know, one revolution is 360 degrees.
  - There is nothing special about the number 360 [some say it is used as it is roughly the number of days in a year] but any other number would also work.
  - We could have 400 units in a complete revolution [so 100 units in a right angle].
  - In fact, there is a measure of angles that uses 100 to be a right angle – it is called “Gradians” [you will see a “grad” setting on your calculator].
  - All these angle measures are a bit arbitrary48 but there is one measure for angles that is more natural than all the others, and that is “radians”.49 So how big is one radian?
  - We take a sector of a circle of radius 1 and arc length also
- **MM4.3: The values of sine, cosine, and tangent for the angles 0°, 30°, 45°, 60°, 90°.**
  - The values of sine, cosine, and tangent for the angles 0°, 30°, 45°, 60°, 90°.
  - Learn these – standard triangles – and extend them to other ranges [note: tan 90 is not defined]
- **MM4.4: The sine, cosine, and tangent functions; their graphs, symmetries, and periodicity.**
  - The sine, cosine, and tangent functions; their graphs, symmetries, and periodicity.
- **MM4.5: Knowledge and use of tan 𝜃= sin 𝜃 cos 𝜃 sin2 𝜃+ cos2 𝜃= 1 There are many ways to define trigonometric functions.**
  - Knowledge and use of tan 𝜃= sin 𝜃 cos 𝜃 sin2 𝜃+ cos2 𝜃= 1 There are many ways to define trigonometric functions.
  - Usually, we first meet trigonometry in relation to right-angled triangles, and if we use this approach then the formula sin2 𝜃+ cos2 𝜃= 1  is clearly just a version of Pythagoras’ Theorem.
  - We have drawn a diagram to illustrate this.
- **MM4.6: Solution of simple trigonometric equations in a given interval (this may involve the use of the identities in MM4.5); for example: tan 𝑥= − √3 for −𝜋<**
  - Solution of simple trigonometric equations in a given interval (this may involve the use of the identities in MM4.5); for example: tan 𝑥= − √3 for −𝜋< 𝑥< 𝜋; sin2 (2𝑥+ 𝜋 3) = 2 for −2𝜋< 𝑥< 2𝜋; 12 cos2 𝑥+ 6 sin 𝑥−10 = 2 for 0° < 𝑥< 360°.

### MM5: Exponentials and logarithms

- **MM5.1: 𝑦= 𝑎𝑥 and its graph, for simple positive values of 𝑎.**
  - 𝑦= 𝑎𝑥 and its graph, for simple positive values of 𝑎.
  - Make sure you know what the graph of 𝑦= 𝑎𝑥 looks like for different values of 𝑎.
  - Look carefully at 0 < 𝑎< 1 and 𝑎= 1 and 1 < 𝑎  and make sure you can explain their features.
  - What happens to the graphs as 𝑎 gets bigger and bigger?
  - Use a graph drawing package [e.g., DESMOS GRAPHING] to help you if necessary but make sure you think through the results in each and every case.
  - Notice that we do not look at cases when 𝑎< 0.
  - We discussed why we do not look at this case in the discussions earlier when we looked at indices so it might be useful to revisit that discussion.
- **MM5.2: Laws of logarithms: 𝑎𝑏= 𝑐⟺𝑏= log𝑎𝑐 log𝑎𝑥+ log𝑎𝑦= log𝑎(𝑥𝑦) log𝑎𝑥−log𝑎𝑦= log𝑎(𝑥 𝑦) 𝑘log𝑎𝑥= log𝑎(𝑥𝑘) including the special cases: log𝑎 𝑥= −log𝑎𝑥 log𝑎𝑎= 1**
  - Laws of logarithms: 𝑎𝑏= 𝑐⟺𝑏= log𝑎𝑐 log𝑎𝑥+ log𝑎𝑦= log𝑎(𝑥𝑦) log𝑎𝑥−log𝑎𝑦= log𝑎(𝑥 𝑦) 𝑘log𝑎𝑥= log𝑎(𝑥𝑘) including the special cases: log𝑎 𝑥= −log𝑎𝑥 log𝑎𝑎= 1
- **MM5.3: The solution of equations of the form 𝑎𝑥= 𝑏, and equations which can be reduced to this form, including those that need prior algebraic manipulation; **
  - The solution of equations of the form 𝑎𝑥= 𝑏, and equations which can be reduced to this form, including those that need prior algebraic manipulation; for example,  32𝑥= 4 and 25𝑥−3 × 5𝑥+ 2 = 0.
  - Example

### MM6: Differentiation

- **MM6.1: The derivative of 𝑓(𝑥) as the gradient of the tangent to the graph 𝑦= 𝑓(𝑥) at a point.**
  - The derivative of 𝑓(𝑥) as the gradient of the tangent to the graph 𝑦= 𝑓(𝑥) at a point.
- **MM6.2: Differentiation of 𝑥𝑛 for rational n, and related sums and differences.**
  - Differentiation of 𝑥𝑛 for rational n, and related sums and differences.
  - This might require some simplification before differentiating.
  - For example, the ability to differentiate an expression such as (3𝑥+2)2 𝑥 In the TMUA/ESAT, we expect you to be able to differentiate simple expressions involving sums of powers of 𝑥 or expressions that can be simplified to sums of powers of 𝑥.
  - We do NOT expect you to be able to differentiate trigonometric expressions or use rules like the chain rule, the product rule etc.
  - We have kept to the scope of what we expect you to be able to differentiate both narrow and simple because we want to
- **MM6.3: Applications of differentiation to gradients, tangents, normals, stationary points (maxima and minima only), strictly increasing functions [ if 𝑓′(𝑥) **
  - Applications of differentiation to gradients, tangents, normals, stationary points (maxima and minima only), strictly increasing functions [ if 𝑓′(𝑥) > 0 ] and strictly decreasing functions [ if 𝑓′(𝑥) < 0 ].
  - Points of inflexion will not be examined, although a qualitative understanding of points of inflexion in the curves of simple polynomial functions is expected.
  - On of the motivations behind this section of the specification is to equip you with enough basic calculus techniques to help you sketch curves given an equation.
  - As you read through this section and as you think about the ideas we meet, make sure you think about how the ideas relate to the shapes of curves.
  - You ought to have a good idea of the general shape of quadratic curves, cubics, quartics, and quintics and

### MM7: Integration

- **MM7.1: Definite integration as related to the ‘area between a curve and an axis’.**
  - Definite integration as related to the ‘area between a curve and an axis’.
  - The difference between finding a definite integral and finding the area between a curve and an axis is expected to be understood.
  - In this section, we will assume you know how to integrate and deal with limits in an integral!
  - When we talk about areas and integration, we need to be very careful.
  - The term “area” is usually taken to be a positive value and that can lead to some confusion when we talk about definite integration and the area between a curve and an axis.
  - Definite integration is almost a sum of areas but instead it subtracts “areas” that are underneath the 𝑥-axis.
  - So, a definite integral calculates all the areas that sit above the 𝑥-axis and
- **MM7.2: Finding definite and indefinite integrals of 𝑥𝑛 for n rational, 𝑛≠1, and related sums and differences, including expressions which require simplificat**
  - Finding definite and indefinite integrals of 𝑥𝑛 for n rational, 𝑛≠1, and related sums and differences, including expressions which require simplification prior to integrating.
  - For example: ∫(𝑥+ 2)2d𝑥 , and  ∫ (3𝑥−5)2 𝑥 d In the TMUA/ESAT we expect you to be able to integrate sums of terms in powers of 𝑥 using the rule: ∫𝑘𝑥𝑛  d𝑥= 𝑘𝑥𝑛+1
- **MM7.3: An understanding of the Fundamental Theorem of Calculus and its significance to integration.**
  - An understanding of the Fundamental Theorem of Calculus and its significance to integration.
  - Simple examples of its use may be required in the forms: ∫𝑓(𝑥)𝑑𝑥 𝑏 𝑎 = 𝐹(𝑏) −𝐹(𝑎) , where  𝐹′(𝑥) = 𝑓(𝑥) 𝑑 𝑑𝑥∫𝑓(𝑥)𝑑𝑥 𝑥
- **MM7.4: Combining integrals with either equal or contiguous ranges.**
  - Combining integrals with either equal or contiguous ranges.
- **MM7.5: Approximation of the area under a curve using the trapezium rule; determination of whether this constitutes an overestimate or an underestimate.**
  - Approximation of the area under a curve using the trapezium rule; determination of whether this constitutes an overestimate or an underestimate.
  - We expect you to be able to use the Trapezium rule to estimate areas under curves [and recall we take area to be positive] or to estimate the values of definite integrals [remember definite integrals take “areas” under the 𝑥-axis as negative].
  - We will make sure that any question we ask in the TMUA/ESAT is very clear about whether it is asking for an estimate of areas between a curve and an axis or whether it is asking for an estimate of a definite integral.
- **MM7.6: Solving differential equations of the form 𝑑𝑦 𝑑𝑥= 𝑓(𝑥) Solving the expression 𝑑𝑦 𝑑𝑥= 𝑓(𝑥) is really asking you to find what 𝑦 is, expressed in terms o**
  - Solving differential equations of the form 𝑑𝑦 𝑑𝑥= 𝑓(𝑥) Solving the expression 𝑑𝑦 𝑑𝑥= 𝑓(𝑥) is really asking you to find what 𝑦 is, expressed in terms of 𝑥, such that when you differentiate 𝑦 you get 𝑓(𝑥).
  - This is a bit of a mouthful.
  - Another way of saying this is: what do you differentiate to get 𝑓(𝑥)?
  - We will look at a couple of examples, firstly without any additional conditions and then with additional conditions [you will see what we mean by additional conditions below]:

### MM8: Graphs of functions

- **MM8.1: Recognise and be able to sketch the graphs of common functions that appear in this specification: these include lines, quadratics, cubics, trigonometr**
  - Recognise and be able to sketch the graphs of common functions that appear in this specification: these include lines, quadratics, cubics, trigonometric functions, logarithmic functions, exponential functions, square roots, and the modulus function.
- **MM8.2: Knowledge of the effect of simple transformations on the graph of 𝑦= 𝑓(𝑥) with positive or negative value of 𝑎 as represented by  𝑦= 𝑎𝑓(𝑥) , 𝑦= 𝑓(𝑥) +**
  - Knowledge of the effect of simple transformations on the graph of 𝑦= 𝑓(𝑥) with positive or negative value of 𝑎 as represented by  𝑦= 𝑎𝑓(𝑥) , 𝑦= 𝑓(𝑥) + 𝑎 ,  𝑦= 𝑓(𝑥+ 𝑎) , 𝑦= 𝑓(𝑎𝑥) Compositions of these transformations.
  - Knowledge and use of the notation 𝑓(𝑔(𝑥)).
  - This topic tends to be poorly understood.
  - Usually, when these ideas are first met, students tend to learn the rules without much understanding of what is going on.
  - It is made more tricky by the fact that some of the ways graphs shift tend to be exactly opposite of what you might first expect;  for instance,  𝑦= 𝑓(𝑥+ 𝑎) looks like it ought to shift [translate] the graph of 𝑦= 𝑓(𝑥) to the right [in the positive 𝑥 direction] by a distance 𝑎 BUT THAT IS WRONG!!
- **MM8.3: Understand how altering the values of 𝑚 and 𝑐 affects the graph of  𝑦= 𝑚𝑥+ 𝑐.**
  - Understand how altering the values of 𝑚 and 𝑐 affects the graph of  𝑦= 𝑚𝑥+ 𝑐.
  - To understand how 𝑚 and 𝑐 affects the graph of  𝑦= 𝑚𝑥+ 𝑐 consider either of the following sequence of transformation.
  - You will need to use your knowledge of graph transformations that we discussed above and make use of a graph sketching package too to enhance your understanding: 𝑦= 𝑥 →𝑦= 𝑚𝑥 →𝑦= 𝑚(𝑥+ 𝑐 𝑚) = 𝑚𝑥+ 𝑐 𝑦= 𝑥 →𝑦= 𝑥+ 𝑐 →𝑦= 𝑚𝑥+ 𝑐 Exercise How did you deal with 𝑦= 𝑥 →𝑦= 𝑥+ 𝑐 above?
  - Did you use 𝑓(𝑥) + 𝑐 or 𝑓(𝑥+ 𝑐) ?
- **MM8.4: Understand how altering the values of 𝑎, 𝑏 and 𝑐 in 𝑦= 𝑎(𝑥+ 𝑏)2 + 𝑐 affects the corresponding graph.**
  - Understand how altering the values of 𝑎, 𝑏 and 𝑐 in 𝑦= 𝑎(𝑥+ 𝑏)2 + 𝑐 affects the corresponding graph.
- **MM8.5: Use differentiation to help determine the shape of the graph of a given function; including finding stationary points (excluding inflexions); and when**
  - Use differentiation to help determine the shape of the graph of a given function; including finding stationary points (excluding inflexions); and when the function is increasing or decreasing.
- **MM8.6: Use algebraic techniques to determine where the graph of a function intersects the coordinate axes; appreciate the possible numbers of real roots a ge**
  - Use algebraic techniques to determine where the graph of a function intersects the coordinate axes; appreciate the possible numbers of real roots a general polynomial can possess.
- **MM8.7: Geometric interpretation of algebraic solutions of equations; relationship between the intersections of two graphs and the solutions of the correspond**
  - Geometric interpretation of algebraic solutions of equations; relationship between the intersections of two graphs and the solutions of the corresponding simultaneous equations.


## Module P: Physics

### P1: Electricity

- **P1.1: Electrostatics**
  - (a) Know and understand that insulators can be charged by friction.
  - (b) Know and understand that charging is caused by gain or loss of electrons.
  - (c) Know and understand that like charges repel and unlike charges attract.
  - (d) Understand applications and hazards associated with electrostatics, including the role of earthing.
- **P1.2: Electric circuits**
  - (a) Know and recognise the basic circuit symbols and diagrams, including: cell, battery, light source, resistor, variable resistor, ammeter, voltmeter, switch, diode.
  - (b) Understand the difference between alternating current (ac) and direct current (dc).
  - (c) Understand the difference between conductors and insulators, and recall examples of each type.
  - (d) Know and be able to apply: 𝑐𝑢𝑟𝑟𝑒𝑛𝑡= 𝑐ℎ𝑎𝑟𝑔𝑒 𝑡𝑖𝑚𝑒 , 𝐼= 𝑄 𝑡

### P2: Magnetism

- **P2.1: Properties of magnets**
  - (a) Know and be able to use the terms north pole, south pole, attraction and repulsion.
  - (b) Know the magnetic field pattern around a bar magnet (including direction).
  - (c) Understand the difference between soft and hard magnetic materials (e.g. iron and steel).
  - (d) Qualitatively understand induced magnetism. Know and be able to use the terms north pole, south pole, attraction and repulsion Permanent magnets have two poles, a north pole (N) at one end and south pole (S) at the other. Magnets come in different shapes and sizes, e.g.: Magnets exert forces on one 
- **P2.2: Magnetic field due to an electric current**
  - (a) Know and understand the magnetic effect of a current.
  - (b) Know the magnetic field patterns around current-carrying wires (including direction) for straight wires and coils/solenoids.
  - (c) Know and understand the factors affecting magnetic field strength around a wire.
  - (d) Understand the difference between permanent magnets and electromagnets. Know and understand the magnetic effect of a current Electric currents create magnetic fields in the surrounding space. This can be demonstrated by placing a small magnetic compass close to a current-carrying conductor and then 
- **P2.3: The motor effect**
  - (a) Know that a wire carrying a current in a magnetic field can experience a force.
  - (b) Know the factors affecting the direction of a force on a wire in a magnetic field (including the left- hand rule).
  - (c) Know the factors affecting the magnitude of the force on a wire in a magnetic field.
  - (d) Know and be able to apply F = BIL for a straight wire at right angles to a uniform magnetic field.
  - (e) Know and understand the construction and operation of a dc motor, including factors affecting the magnitude of the force produced.
  - (f) Understand applications of electromagnets. Know that a wire carrying a current in a magnetic field can experience a force
- **P2.4: Electromagnetic induction**
  - (a) Know and understand that a voltage is induced when a wire cuts magnetic field lines, or when a magnetic field changes.
  - (b) Know the factors affecting the magnitude of an induced voltage.
  - (c) Know the factors affecting the direction of an induced voltage.
  - (d) Understand the operation of an ac generator, including factors affecting the output voltage.
  - (e) Interpret the graphical representation of the output voltage of a simple ac generator.
  - (f) Understand applications of electromagnetic induction. Know and understand that a voltage is induced when a wire cuts magnetic field lines, or when a magnetic field changes
- **P2.5: Transformers**
  - (a) Know and understand the terms step-up transformer and step-down transformer.
  - (b) Know and use the relationship between the number of turns on the primary and secondary coils, and the voltage ratio: 𝑉𝑝 𝑉𝑠= 𝑛𝑝 𝑛𝑠
  - (c) Know that a consequence of 100% efficiency is total transfer of electrical power, and that this gives rise to the following relationship: Vp Ip = Vs Is. Know and use this relationship to solve problems.

### P3: Mechanics

- **P3.1: Kinematics**
  - (a) Know and understand the difference between scalar and vector quantities.
  - (b) Know and understand the difference between distance and displacement and between speed and velocity.
  - (c) Know and be able to apply:    speed = distance time  ,   velocity = change in dispacement time
  - (d) Know and be able to apply:     acceleration =
- **P3.2: Forces**
  - (a) Understand that there are different types of force, including weight, normal contact, drag (including air resistance), friction, magnetic, electrostatic, thrust, upthrust, lift and tension.
  - (b) Know and understand the factors that can affect the magnitude and direction of the forces in 3.2a.
  - (c) Draw and interpret force diagrams.
  - (d) Qualitatively understand resultant force, with calculations in one dimension. Understand that there are different types of force, including weight, normal contact, drag (including air resistance), friction, magnetic, electrostatic, thrust, upthrust, lift and tension Know and understand the factors t
- **P3.3: Force and extension**
  - (a) Interpret force–extension graphs.
  - (b) Understand elastic and inelastic extension, and elastic limits.
  - (c) Know and be able to apply Hooke’s law (F = k x), and understand the meaning of the limit of proportionality.
  - (d) Understand energy stored in a stretched spring as: 𝐸= 2 𝐹𝑥= 2 𝑘𝑥2 Interpret force–extension graphs
- **P3.4: Newton’s laws**
  - (a) Know and understand Newton’s first law as: ‘a body will remain at rest or in a state of uniform motion in a straight line unless acted on by a resultant external force’.
  - (b) Understand mass as a property that resists change in motion (inertia).
  - (c) Know and understand Newton’s second law as: force = mass × acceleration
  - (d) Know and understand Newton’s third law as: ‘if body A exerts a force on body B then body B exerts an equal and opposite force of the same type on body A’. Know and understand Newton’s first law as: ‘A body will remain at rest or in a state of uniform motion in a straight line unless acted on by a re
- **P3.5: Mass and weight**
  - (a) Know and understand the difference between mass and weight.
  - (b) Know and be able to apply gravitational field strength, g, approximated as 10 N kg–1 on Earth.
  - (c) Know and be able to apply the relationship between mass and weight: w = mg
  - (d) Understand free-fall acceleration.
  - (e) Know the factors affecting air resistance.
  - (f) Understand terminal velocity and the forces involved. Know and understand the difference between mass and weight
- **P3.6: Momentum**
  - (a) Know and be able to apply:  momentum = mass × velocity,  p = mv
  - (b) Know and be able to use the law of conservation of momentum in calculations in one dimension.
  - (c) Know and be able to apply:  force = rate of change of momentum. Know and be able to apply: momentum = mass × velocity,  p = mv
- **P3.7: Energy**
  - (a) Know and be able to apply: work = force × distance moved (in direction of force)
  - (b) Understand work done as a transfer of energy.
  - (c) Know and be able to apply: gravitational potential energy = mgh, where h is the difference in height of the object.
  - (d) Know and be able to apply: kinetic energy = 2 𝑚𝑣2
  - (e) Know and be able to apply:  power = energy transfer time

### P4: Thermal physics

- **P4.1: Conduction**
  - (a) Know and understand thermal conductors and insulators, with examples.
  - (b) Know and be able to apply factors affecting rate of conduction. Know and understand thermal conductors and insulators, with examples Thermal energy Solids, liquids and gases are all made of microscopic particles – atoms or molecules (or ions). These particles are in motion: in solids the particles v
- **P4.2: Convection**
  - (a) Understand and be able to apply the effect of temperature on density of fluid.
  - (b) Understand and be able to apply fluid flow caused by differences in density. Understand and be able to apply the effect of temperature on density of fluid When the temperature of a fluid increases, the average speed of its microscopic particles increases. The particles collide with each other more f
- **P4.3: Thermal radiation**
  - (a) Understand thermal radiation as electromagnetic waves in the infrared region.
  - (b) Know and be able to apply absorption and emission of radiation.
  - (c) Know and be able to apply factors affecting rate of absorption and emission of thermal radiation. Understand thermal radiation as electromagnetic waves in the infrared region Thermal radiation, also called infrared (IR) radiation, is a type of wave that is one of the parts of the electromagnetic spe
- **P4.4: Heat capacity**
  - (a) Understand the effect of energy transferred to or from an object on its temperature.
  - (b) Know and be able to apply: specific heat capacity = thermal energy mass ×temperature change where temperature is measured in °C and specific heat capacity, 𝑐,  is measured in J kg–1 °C–1. Understand the effect of energy transferred to or from an object on its temperature Heat may be transferred to o

### P5: Matter

- **P5.1: States of matter**
  - (a) Know the characteristic properties of solids, liquids and gases.
  - (b) Know and be able to apply particle models of solids, liquids and gases.
  - (c) Know and be able to explain properties of solids, liquids and gases in terms of particle motion and the forces and distances between the particles. Know the characteristic properties of solids, liquids and gases Each of the three states of matter – solid, liquid and gas – has characteristic properti
- **P5.2: Ideal gases**
  - (a) Be able to explain pressure and temperature in terms of the behaviour of particles.
  - (b) Understand and be able to apply the effect of pressure (P ) on gas volume (V ) at constant temperature, i.e. PV = constant. Be able to explain pressure and temperature in terms of the behaviour of particles According to the particle model, a gas consists of identical particles which are in random mo
- **P5.3: State changes**
  - (a) Understand the terms melting point and boiling point.
  - (b) Know and understand the terms latent heat of fusion and latent heat of vaporisation.
  - (c) Know and be able to apply specific latent heat calculations. Understand the terms melting point and boiling point Nearly every pure substance has a melting point and a boiling point. (There are a few exceptions, such as carbon dioxide, which sublime – change directly between the solid and gas states
- **P5.4: Density**
  - (a) Know and be able to apply:  density = mass volume ,     𝜌= 𝑚 𝑉
  - (b) Understand the experimental determination of densities.
  - (c) Be able to compare the densities of solids, liquids and gases. Know and be able to apply:  𝒅𝒆𝒏𝒔𝒊𝒕𝒚= 𝒎𝒂𝒔𝒔
- **P5.5: Pressure**
  - (a) Know and be able to apply:   pressure = force area
  - (b) Know and be able to apply: hydrostatic pressure = ℎ𝜌g, where ℎ is the height, or depth, of the liquid. Know and be able to apply: 𝒑𝒓𝒆𝒔𝒔𝒖𝒓𝒆= 𝒇𝒐𝒓𝒄𝒆 𝒂𝒓𝒆𝒂 When a force is exerted on a surface, the pressure on the surface is defined by the relationship 𝑝𝑟𝑒𝑠𝑠𝑢𝑟𝑒= 𝑓𝑜𝑟𝑐𝑒

### P6: Waves

- **P6.1: Wave properties**
  - (a) Understand the transfer of energy without net movement of matter.
  - (b) Know and understand transverse and longitudinal waves.
  - (c) Know and understand the terms: peak, trough, compression and rarefaction.
  - (d) Recall examples of waves, including electromagnetic waves and sound.
  - (e) Know and be able to use the terms: amplitude, wavelength, frequency and period.
  - (f) Know and be able to apply: frequency = period  ,  𝑓= 𝑇
  - (g) Know and be able to apply:  wave speed =
- **P6.2: Wave behaviour**
  - (a) Know and understand reflection at a surface.
  - (b) Know and understand refraction at a boundary.
  - (c) Know and understand the effect of reflection and refraction on the speed, frequency, wavelength and direction of waves.
  - (d) Know and understand the analogy of reflection and refraction of light with that of water waves.
  - (e) Know and understand the Doppler effect. Know and understand reflection at a surface When a wave strikes a surface, all or part of the wave energy can reflect off the surface. The diagram below shows how waves reflect from a smooth surface.
- **P6.3: Optics**
  - (a) Draw and interpret ray diagrams to describe reflection in plane mirrors.
  - (b) Know and be able to apply:  angle of incidence = angle of reflection
  - (c) Draw and interpret ray diagrams for refraction at a planar boundary.
  - (d) Know and be able to interpret angle of incidence and angle of refraction.
  - (e) Know and understand the effect of refraction on wave direction (away from or towards the normal) and speed (increasing or decreasing). Draw and interpret ray diagrams to describe reflection in plane mirrors Know and be able to apply: angle of incidence = angle of reflection
- **P6.4: Sound waves**
  - (a) Understand the production of sound waves by a vibrating source.
  - (b) Understand the need for a medium.
  - (c) Understand qualitatively the relation of loudness to amplitude and pitch to frequency.
  - (d) Know and understand longitudinal waves.
  - (e) Understand that reflection causes echoes.
  - (f) Recall that the range of human hearing is 20 Hz to 20 kHz.
  - (g) Know and understand ultrasound and its uses (sonar and medical scanning). Understand the production of sound waves by a vibrating source Sound waves are produced by a vibrating source.
- **P6.5: Electromagnetic spectrum**
  - (a) Know and understand the nature and properties of electromagnetic waves (they are transverse waves and travel at the speed of light in a vacuum).
  - (b) Recall the component parts of the spectrum (radio waves, microwaves, IR, visible light, UV, X-rays, gamma).
  - (c) Understand the distinction of the component parts by different wavelengths and/or frequencies.
  - (d) Recall the order of the component parts by wavelength and/or frequency.
  - (e) Understand applications and hazards of the component parts of the electromagnetic spectrum. Know and understand the nature and properties of electromagnetic waves (they are transverse waves and travel at the speed of light in a vacuum)

### P7: Radioactivity

- **P7.1: Atomic structure**
  - (a) Understand the atom in terms of protons, neutrons and electrons.
  - (b) Know and be able to apply the nuclear model of atomic structure.
  - (c) Know the relative charges and masses of protons, neutrons and electrons.
  - (d) Understand and be able to use the terms atomic number and mass number.
  - (e) Know and understand the term isotope.
  - (f) Know and understand the term nuclide, and use nuclide notation.
  - (g) Understand that ionisation is caused by the gain/loss of electrons. Understand the atom in terms of protons, neutrons and electrons Know and be able to apply the nuclear model of atomic structure
- **P7.2: Radioactive decay**
  - (a) Know and understand that emissions arise from an unstable nucleus.
  - (b) Know and understand the random nature of emissions.
  - (c) Know and understand the differences between alpha, beta and gamma emission.
  - (d) Know and understand the nature of alpha and beta particles, and gamma radiation.
  - (e) Be able to use and interpret nuclear equations.
  - (f) Know the effect of decay on atomic number and mass number. Know and understand that emissions arise from an unstable nucleus There are many naturally occurring nuclides. Some of these types of nucleus are stable and others are unstable. Nuclei that are stable will continue to exist indefinitely.
- **P7.3: Ionising radiation**
  - (a) Know the relative penetrating abilities of alpha, beta and gamma radiation.
  - (b) Know the relative ionising abilities of alpha, beta and gamma radiation.
  - (c) Understand qualitatively the deflection of alpha, beta and gamma radiation in electric or magnetic fields.
  - (d) Know and appreciate the existence of background radiation.
  - (e) Understand the applications and hazards of ionising radiation. Know the relative penetrating abilities of alpha, beta and gamma radiation The penetrating ability of a type of radiation refers to how easily it can pass through materials. Gamma is the most penetrating of the three types of nuclear rad
- **P7.4: Half-life**
  - (a) Be able to interpret graphical representations of radioactive decay (including consideration of decay products).
  - (b) Understand the meaning of the term half-life.
  - (c) Understand and be able to apply half-life calculations. Be able to interpret graphical representations of radioactive decay (including consideration of decay products) The half-life of a radioactive source can be read from a graph of count rate against time (or from a graph of number of remaining un


## Module C: Chemistry

### C1: Atomic structure

- **C1.1: Describe the structure of the atom as a central nucleus (containing protons and neutrons) surrounded by electrons moving in shells/energy levels.**
  - Describe the structure of the atom as a central nucleus (containing protons and neutrons) surrounded by electrons moving in shells/energy levels.
- **C1.2: Know the relative masses and charges of protons, neutrons and electrons, and recognise that most of the mass of an atom is in the nucleus.**
  - Know the relative masses and charges of protons, neutrons and electrons, and recognise that most of the mass of an atom is in the nucleus.
- **C1.3: Know and be able to use the terms atomic number and mass number, together with standard notation (e.g.**
  - Know and be able to use the terms atomic number and mass number, together with standard notation (e.g.
  - C ), and so be able to calculate the number of protons, neutrons and electrons in any atom or ion.
  - Electrons move around the nucleus.
  - It has been found that electrons can have only certain energies and, for electron counting purposes, a diagram with concentric circles to represent the shells/energy levels and dots or crosses to represent the electrons is used.
  - Remember though that atoms are 3-dimensional objects and not flat as the ‘dot and cross’ diagrams suggest.
- **C1.4: Use the atomic number to write the electron configurations of the first 20 elements in the Periodic Table (H to Ca) in comma-separated format (e.g.**
  - Use the atomic number to write the electron configurations of the first 20 elements in the Periodic Table (H to Ca) in comma-separated format (e.g.
  - 2,8,8,1 for a potassium atom).
  - To determine the electron configuration of a positively charged ion, remember that electrons have been removed from the highest occupied shell of the atom.
  - The number of electrons removed is the same as the charge.
  - For example, a potassium ion has the formula K+, the ion has a single positive charge, so the electron configuration of the K+ ion is 2,8,8.
  - To determine the electron configuration of a negatively charged ion, remember that electrons have been added to the atom.
  - The number of electrons added is the same as the charge.
  - For example, Fluorine has atomic number 9 and fluoride ions have the formula F−.
- **C1.5: Know the definition of isotopes as atoms of an element with the same number of protons but different numbers of neutrons (so having different mass num**
  - Know the definition of isotopes as atoms of an element with the same number of protons but different numbers of neutrons (so having different mass numbers).
  - Use data, including that from a mass spectrometer, to identify the number and abundances of different isotopes of elements.
  - A mass spectrum shows the mass-to-charge ratio (m/z) of the ions on the x-axis, and the y-axis gives information on the number of ions of any particular m/z value detected.
  - The y-axis may have ‘arbitrary units’ or might show relative abundance.
  - If relative abundance is shown, the m/z peak caused by the most abundant ion is given a value of 100% and all other peaks are then given heights relative to this Mass spectrum of neon
- **C1.6: Know and use the concept of relative atomic mass, Ar , including calculating values from given data.**
  - Know and use the concept of relative atomic mass, Ar , including calculating values from given data.
  - With data presented as percentages:  a% of X q ,  b% of X r ,  c% of X s , ...
  - in a sample of 100 atoms of the element: a have a mass of q, b have a mass of r, and c have a mass of s, ...

### C2: The Periodic Table

- **C2.1: Know that Periods are horizontal rows and Groups are vertical columns.**
  - Know that Periods are horizontal rows and Groups are vertical columns.
- **C2.2: Know that the elements are arranged in the order of increasing atomic number.**
  - Know that the elements are arranged in the order of increasing atomic number.
- **C2.3: Recall the position of metals and non-metals in the Periodic Table: alkali metals (Group 1), alkaline earth metals (Group 2), common non-metals in Gro**
  - Recall the position of metals and non-metals in the Periodic Table: alkali metals (Group 1), alkaline earth metals (Group 2), common non-metals in Group 16, the halogens (Group 17), the noble gases (Group 18) and the transition metals.
- **C2.4: Know and use the relationship between the position of an atom in the Periodic Table (Group and Period) and the electron configuration of the atom.**
  - Know and use the relationship between the position of an atom in the Periodic Table (Group and Period) and the electron configuration of the atom.
- **C2.5: Understand that elements in the same Group have similar chemical properties and that down a metal Group, reactivity increases and down a non-metal Gro**
  - Understand that elements in the same Group have similar chemical properties and that down a metal Group, reactivity increases and down a non-metal Group, reactivity decreases.
  - In the following shortened and simplified version of the table, the electron configurations have been included to illustrate these patterns.
  - Shortened Periodic Table

### C3: Chemical reactions, formulae and equations

- **C3.1: Understand that in a chemical reaction, new substances are formed by the rearrangement of atoms and their electrons, but no nuclei are destroyed or cr**
  - Understand that in a chemical reaction, new substances are formed by the rearrangement of atoms and their electrons, but no nuclei are destroyed or created.
  - When 2.47 g of green copper carbonate is heated, 1.59 g of black copper oxide remains.
  - Which of the following statements is/are correct?
  - 1) A chemical reaction has occurred 2) 0.88 g of copper carbonate has melted 3) 0.88 g of carbon dioxide has been released 4) 0.88 g of carbon dioxide has vaporised 5) 0.88 g of atoms have been destroyed
- **C3.2: Know the chemical formulae of simple, common ionic and covalent compounds.**
  - Know the chemical formulae of simple, common ionic and covalent compounds.
  - Ionic compounds The formula of ionic compounds that contain common ions can be worked out.
  - The tables below show the charge of common ions.
  - Some of these, as shown, are linked to their position in the Periodic Table.
  - positive ions Group 1 ions Group 2 ions Group 13 ions other positive ions
- **C3.3: Know and use state symbols: solid (s), liquid (l), gas (g), aqueous solution (aq).**
  - Know and use state symbols: solid (s), liquid (l), gas (g), aqueous solution (aq).
  - When magnesium metal reacts with sulfuric acid, hydrogen is given off and a solution of magnesium sulfate is formed.
  - Write a balanced equation for this reaction including state symbols.
- **C3.4: Be able to construct and balance a chemical equation, including ionic and half- equations.**
  - Be able to construct and balance a chemical equation, including ionic and half- equations.
  - Step 3 If the equation is not balanced, then add in more of the substance that provides the missing atoms.
  - The formula of a substance must never be changed (for example, here the formula of water cannot be changed to make the equation
- **C3.5: Understand that often chemical reactions can be reversible and do not go to completion. All of the reactants do not turn fully into the products but the reaction reaches a state of equilibrium in a closed system.**
  - (a) Know the factors that can affect the position of an equilibrium (concentration of reactants/products, temperature, overall pressure).
  - (b) Predict the effect of changing these factors on the position of equilibrium. 1) Changing the concentration of reactants/products add more reactants remove some

### C4: Quantitative chemistry

- **C4.1: Use Ar values to calculate the relative molar mass, Mr.**
  - Use Ar values to calculate the relative molar mass, Mr.
- **C4.2: Know that Avogadro’s number gives the number of particles in one mole of a substance.**
  - Know that Avogadro’s number gives the number of particles in one mole of a substance.
- **C4.3: Know that one mole of a substance is the Ar or Mr in grams, and perform conversions of grams to moles and vice versa (including working in tonnes and **
  - Know that one mole of a substance is the Ar or Mr in grams, and perform conversions of grams to moles and vice versa (including working in tonnes and kilograms).
  - Know that the amount of a substance corresponds to the number of moles of a substance.
  - A balloon contains 0.200 mol of helium.
  - How many atoms of helium are contained in the balloon?
  - [NA = 6.022 × 1023 mol−1]
- **C4.4: Calculate the percentage composition by mass of a compound using given Ar values.**
  - Calculate the percentage composition by mass of a compound using given Ar values.
- **C4.5: Know that the empirical formula is the simplest integer ratio of atoms in a compound.**
  - Know that the empirical formula is the simplest integer ratio of atoms in a compound.
  - Find the empirical formula of a compound from a variety of data, such as the percentage composition by mass of the elements present or reacting masses.
  - Find the molecular formula from the empirical formula if given the Mr value.
  - What is the percentage by mass of carbon in glucose, C6H12O6?
  - [Ar values: H = 1.0; C = 12.0; O = 16.0] The percentage of water in a hydrated compound can also be calculated in a similar manner.
- **C4.6: Use balanced chemical equations to calculate the masses of reactants and products, including if there is a limiting reactant present.**
  - Use balanced chemical equations to calculate the masses of reactants and products, including if there is a limiting reactant present.
- **C4.7: Be able to construct balanced chemical equations from reacting masses or gas volumes data.**
  - Be able to construct balanced chemical equations from reacting masses or gas volumes data.
- **C4.8: Understand that (for an ideal gas) one mole of a gas occupies a set volume at a given temperature and pressure (for example, 24 dm3 at room temperatur**
  - Understand that (for an ideal gas) one mole of a gas occupies a set volume at a given temperature and pressure (for example, 24 dm3 at room temperature and pressure (rtp)), and perform conversions of volumes to number of moles, and vice versa.
  - What is the maximum mass of magnesium oxide that can be formed if 0.12 g of magnesium is completely burned in excess oxygen?
  - [Ar values: O = 16; Mg = 24] In the manufacture of calcium carbide: CaO(s)  +  3C(s)  →  CaC2(s)  +  CO(g) What is the maximum mass of calcium carbide that can be obtained from 11.2 kg of calcium oxide and 11.2 kg of carbon?
- **C4.9: Solutions**
  - (a) Understand that concentration can be measured in mol dm–3 or g dm–3, and be able to calculate the concentration given the number of moles (or mass) of solute and the volume of solution.
  - (b) Know the term saturated solution, be able to calculate solubility and interpret solubility data.
- **C4.10: Use the concentrations of solutions (or find the concentrations from given data) and the reacting ratio of reactants from the balanced equation to per**
  - Use the concentrations of solutions (or find the concentrations from given data) and the reacting ratio of reactants from the balanced equation to perform titration calculations.
  - What is the concentration, in g dm−3, of a solution of 8.0 g sodium hydroxide dissolved in 5.0 dm3 of solution?
- **C4.11: the equation: percentage yield  = actual yield (g) predicted yield (g) × 100 25.0 g of ethanoic acid, CH3COOH, are formed from the oxidation of 23.0 g**
  - the equation: percentage yield  = actual yield (g) predicted yield (g) × 100 25.0 g of ethanoic acid, CH3COOH, are formed from the oxidation of 23.0 g of ethanol, CH3CH2OH.
  - CH3CH2OH  +  2[O]  →  CH3COOH  +  H2O What is the percentage yield of this reaction?
  - [Ar values = H = 1.0; C = 12.0; O = 16.0]

### C5: Oxidation, reduction and redox

- **C5.1: Know that on a basic level, oxidation is the gain of oxygen and that reduction is the removal of oxygen.**
  - Know that on a basic level, oxidation is the gain of oxygen and that reduction is the removal of oxygen.
- **C5.2: Know and be able to use the concept that oxidation and reduction are the transfer of electrons, i.e.**
  - Know and be able to use the concept that oxidation and reduction are the transfer of electrons, i.e.
  - reduction is the gain of electrons and oxidation is the loss of electrons.
- **C5.4: Identify any chemical equation that involves: oxidation only, reduction only, redox (both oxidation and reduction taking place), or no oxidation/reduc**
  - Identify any chemical equation that involves: oxidation only, reduction only, redox (both oxidation and reduction taking place), or no oxidation/reduction.
  - (C5.3 is covered on pages 72 to 76.)
- **C5.3: Determine and use the oxidation states of atoms in simple inorganic compounds.**
  - Determine and use the oxidation states of atoms in simple inorganic compounds.
  - Rules for assigning oxidation states to atoms
- **C5.5: Understand the concept of disproportionation and recognise reactions (or species) where this occurs.**
  - Understand the concept of disproportionation and recognise reactions (or species) where this occurs.
  - Further examples of disproportionation 1) The reaction of chlorine with a cold dilute sodium hydroxide solution.
  - 2NaOH  +  Cl2  →  NaCl  +  NaClO  +  H2O The oxidation state of the chlorine atoms in Cl2 is zero, because the chlorine is in its elemental state.
  - The oxidation state of the chlorine in sodium chloride is −1.
  - The oxidation state of the Na is +1, and hence to give a sum of the oxidation states equal to zero, the Cl must have an oxidation state of −1.
  - The oxidation state of the Cl in NaClO is +1.
  - The oxidation state of the Na is +1 and that of the O is
- **C5.6: Understand the terms oxidising agent and reducing agent, and be able to identify them in reactions.**
  - Understand the terms oxidising agent and reducing agent, and be able to identify them in reactions.
  - In terms of loss/gain of electrons: An oxidising agent oxidises something else.
  - Oxidation is a loss of electrons, so the oxidising agent must take the electrons that are being lost.
  - Hence the oxidising agent gains electrons and is itself reduced.
  - A reducing agent reduces something else.
  - Reduction is a gain of electrons, so the reducing agent must supply the electrons that are being gained.
  - Hence the reducing agent loses electrons and is itself oxidised.
  - For example, consider the reaction between zinc and aqueous copper(II) ions.

### C6: Chemical bonding, structure and properties

- **C6.1: Define and understand the differences between elements, compounds and mixtures.**
  - Define and understand the differences between elements, compounds and mixtures.
- **C6.2: Understand that atoms often react to form compounds which have the electron configuration of a noble gas (Group 18).**
  - Understand that atoms often react to form compounds which have the electron configuration of a noble gas (Group 18).
  - Understand that the type of bonding taking place depends on the atoms involved in the reaction.
- **C6.3: Ionic bonding**
  - (a) Know that ions are formed by transfer of electrons from atoms of metals to atoms of non-metals, and that these ions (of opposite charge) attract to form ionic compounds.
  - (b) Predict the charge of the most stable ions formed from elements in Groups 1, 2, 16 and 17 and aluminium by consideration of their electron configuration.
  - (c) Know the chemical formulae of common compound ions, e.g. CO32– and OH–.
  - (d) Know that when an element can exist in more than one oxidation state, e.g. Cu, Fe, then Roman numerals are used to denote the one present, e.g. iron(III) chloride for FeCl3.
- **C6.4: Covalent bonding**
  - (a) Know that a covalent bond is formed when atoms share one (or more) pair(s) of electrons, generally between non-metals.
  - (b) Understand that covalently bonded substances can be small molecules (e.g. water, ammonia, methane) or giant structures (e.g. diamond, graphite, silicon dioxide).
  - (c) Understand the general physical properties of substances composed of small molecules or of those that exist as giant covalent structures.
- **C6.5: Metallic bonding**
  - (a) Understand that solid metals exist as a giant structure of positively charged ions surrounded by delocalised (free) electrons.
  - (b) Understand the general physical properties of metals, such as melting point and conductivity.
- **C6.6: Understand that intermolecular forces can exist between molecules, and that these forces must be overcome in melting and boiling.**
  - Understand that intermolecular forces can exist between molecules, and that these forces must be overcome in melting and boiling.
- **C6.7: Be able to relate structure and bonding to physical properties, such as melting point and conductivity.**
  - Be able to relate structure and bonding to physical properties, such as melting point and conductivity.

### C7: Group chemistry

- **C7.1: Know the physical and chemical properties of the alkali metals (Group 1), the halogens (Group 17) and the noble gases (Group 18).**
  - Know the physical and chemical properties of the alkali metals (Group 1), the halogens (Group 17) and the noble gases (Group 18).
- **C7.2: Describe the trends in chemical reactivity and physical properties of the alkali metals (Group 1) and make predictions based on those trends.**
  - Describe the trends in chemical reactivity and physical properties of the alkali metals (Group 1) and make predictions based on those trends.
  - This includes knowledge of the relative positions of lithium, sodium and potassium in Group 1.
- **C7.3: The halogens (Group 17)**
  - (a) Describe the trends in chemical reactivity and physical properties of the halogens and make predictions based on those trends. This includes knowledge of the relative positions of fluorine, chlorine, bromine and iodine in Group 17.
  - (b) Explain what is meant by a displacement reaction, in terms of reactivity competition, between halogens and halide ions. Physical properties of Group 1 The alkali metals are shiny metallic solids at room temperature.

### C8: Separation techniques

- **C8.1: Know that chemical processes are required to displace constituent elements from their compounds.**
  - Know that chemical processes are required to displace constituent elements from their compounds.
  - Electrolysis Electrolysis is the breakdown of an ionic compound using electricity.
  - For electrolysis to occur, the ions need to be mobile.
  - This can be done either by dissolving the ionic compound in water or by melting it.
  - The mixture containing mobile ions is called the electrolyte.
  - A direct current is then applied through the electrolyte using two electrodes.
  - Positive ions are attracted to the negative electrode (the cathode) and negative ions are attracted to the positive electrode (the anode).
  - Reduction occurs at the cathode and oxidation occurs at the anode.
- **C8.2: Know that physical processes are required to separate mixtures, including miscible/immiscible liquids and dissolved/insoluble solids.**
  - Know that physical processes are required to separate mixtures, including miscible/immiscible liquids and dissolved/insoluble solids.
- **C8.3: Know when to apply the following separation techniques: simple/fractional distillation, paper chromatography (including use of Rf values), use of a se**
  - Know when to apply the following separation techniques: simple/fractional distillation, paper chromatography (including use of Rf values), use of a separating funnel, centrifugation, dissolving, filtration, evaporation and crystallisation.
- **C8.4: Know how to establish the purity of a substance using chromatography.**
  - Know how to establish the purity of a substance using chromatography.
  - Using a separating funnel A separating funnel is used to separate two immiscible liquids.
  - When two immiscible liquids are added to a separating funnel, they form two layers.
  - The upper layer has the lower density.
  - When the tap is opened, the lower layer can be poured out.
  - The narrowing walls of the separating funnel make it easier to close the tap the moment the last drop of the lower layer has passed through.
  - Distillation Distillation (sometimes called simple distillation) is used to separate two substances with differing boiling points.
  - Simple distillation is typically used to separate the solvent from a solution, leaving the solute behind.

### C9: Acids, bases and salts

- **C9.1: Acids**
  - (a) Define an acid as a substance that can form H+(aq) ions or that is an H+ donor.
  - (b) Describe reactions with metals, carbonates, metal hydroxides and metal oxides in which salts are formed.
  - (c) Understand the terms strong, weak, dilute and concentrated.
  - (d) Know that some oxides of non-metals react with water to form acidic solutions.
  - (e) Recall that pH is a measure of H+ ion concentration, and recall that a change of 1 on the pH scale corresponds to a change by a factor of 10 in H+ ion concentration.
  - (f) Know that one mole of some acidic substances is able to form/donate more than
- **C9.2: Bases**
  - (a) Define a base as a substance that can form OH–(aq) ions or that is an H+ acceptor.
  - (b) Understand the terms strong, weak, dilute and concentrated.
  - (c) Know that some oxides and hydroxides of metals react with water to form alkaline solutions. In understanding these terms, it is clearly possible to have a ‘concentrated weak base’ and a ‘dilute strong base’. Reactions of some metal oxides and metal hydroxides with water to form alkaline solutions Aq
- **C9.3: Know that the reaction of an acid with a base can lead to neutralisation and is often exothermic.**
  - Know that the reaction of an acid with a base can lead to neutralisation and is often exothermic.
  - Solutions to Exercises 79 to 90

### C10: Rates of reaction

- **C10.1: Describe the qualitative effects on a rate of reaction of concentration, temperature, particle size, a catalyst and, for gases, pressure.**
  - Describe the qualitative effects on a rate of reaction of concentration, temperature, particle size, a catalyst and, for gases, pressure.
- **C10.2: Know that the rate of reaction can be found by measuring the loss of a reactant or the gain of a product, or by measurement of a physical property ove**
  - Know that the rate of reaction can be found by measuring the loss of a reactant or the gain of a product, or by measurement of a physical property over time, and be able to identify which of these measurements can be used in a given situation.
- **C10.3: Interpret data in graphical form concerning the rate of a reaction.**
  - Interpret data in graphical form concerning the rate of a reaction.
- **C10.4: Use collision theory to explain changes in the rate of a reaction.**
  - Use collision theory to explain changes in the rate of a reaction.
- **C10.5: Understand that particles must have sufficient energy when they collide to react, and that this energy is called the activation energy (Ea).**
  - Understand that particles must have sufficient energy when they collide to react, and that this energy is called the activation energy (Ea).
  - Identify the activation energy on an energy level diagram.
- **C10.6: Know that catalysts**
  - (a) are not used up in a reaction.
  - (b) are chemically unchanged at the end of a reaction.
  - (c) provide an alternative route (reaction mechanism) with a lower activation energy, and interpret this effect on an energy level diagram.
  - (d) do not affect the position of an equilibrium. Reactions may be monitored in a number of ways:

### C11: Energetics

- **C11.1: Understand the concepts of an exothermic reaction, for which ΔH is negative (negative enthalpy change), and an endothermic reaction, for which ΔH is p**
  - Understand the concepts of an exothermic reaction, for which ΔH is negative (negative enthalpy change), and an endothermic reaction, for which ΔH is positive (positive enthalpy change).
- **C11.2: Know that if a reversible reaction is exothermic in one direction, it is endothermic in the other direction.**
  - Know that if a reversible reaction is exothermic in one direction, it is endothermic in the other direction.
- **C11.3: Be able to interpret energy level diagrams.**
  - Be able to interpret energy level diagrams.
- **C11.4: Be able to calculate energy changes from specific heat capacities and changes in temperature in calorimetry experiments.**
  - Be able to calculate energy changes from specific heat capacities and changes in temperature in calorimetry experiments.
- **C11.5: Know that bond breaking is endothermic, and bond formation is exothermic, and be able to use bond energy data to calculate energy changes.**
  - Know that bond breaking is endothermic, and bond formation is exothermic, and be able to use bond energy data to calculate energy changes.
  - Some chemical and all physical changes can be reversed.
  - The enthalpy change in each case will have the same magnitude but the movement of energy will be in opposite directions.
  - An example is the interconversion between anhydrous and hydrated copper(II) sulfate: CuSO4  +  5H2O  →  CuSO4·5H2O When water is added to anhydrous copper(II) sulfate, an exothermic change occurs (steam is visible in the picture).

### C12: Electrolysis

- **C12.1: Understand the terms electrode, cathode (negative electrode), anode (positive electrode) and electrolyte.**
  - Understand the terms electrode, cathode (negative electrode), anode (positive electrode) and electrolyte.
- **C12.2: Understand why direct current (dc), and not alternating current (ac), is used in electrolysis.**
  - Understand why direct current (dc), and not alternating current (ac), is used in electrolysis.
- **C12.3: Understand that in electrolysis at the cathode, the cations (positively charged ions) receive electrons (reduction) to change into atoms or molecules,**
  - Understand that in electrolysis at the cathode, the cations (positively charged ions) receive electrons (reduction) to change into atoms or molecules, and at the anode, the anions (negatively charged ions) lose electrons to form atoms or molecules (oxidation).
- **C12.4: Understand and be able to predict the products of the electrolysis of the following**
  - (a) aqueous solutions (including those of salts), including situations where more than one ion/molecule is attracted to a single electrode
  - (b) molten binary compounds
- **C12.5: Be able to write half-equations for the processes taking place at each electrode.**
  - Be able to write half-equations for the processes taking place at each electrode.
- **C12.6: Explain how electrolysis is used to electroplate objects.**
  - Explain how electrolysis is used to electroplate objects.
  - attracted to the anode (positive electrode) where they lose electrons and are oxidised to form neutral atoms/molecules.
  - Electrons flow in the external circuit from the positive electrode to the negative electrode.
  - The oxidised/reduced ions produce pure elements.
  - The types of process caused by electron loss or gain can be remembered using ‘OIL RIG’:

### C13: Carbon/Organic chemistry

- **C13.1: General concepts**
  - (a) Know that crude oil is the main source of hydrocarbons and that it is separated into fractions by fractional distillation (names and uses of specific fractions not expected).
  - (b) Understand the link between carbon chain length and the following trends in physical properties of hydrocarbons: boiling points, viscosity, flammability.
  - (c) Know the use of longer chain alkanes in cracking to form shorter chain alkanes and alkenes, and be able to write balanced chemical equations for these reactions.
  - (d) Understand structural isomerism and be able to recognise examples.
  - (e) Understand and be able to use the following terms: molecular formula, full structural formula (displayed structure) and condensed structural formula.
- **C13.2: Alkanes (saturated hydrocarbons)**
  - (a) Describe alkanes as a homologous series with the general formula of CnH2n+2.
  - (b) Be able to name, or recognise from the name, the C1 to C6 straight-chain alkanes.
- **C13.3: Alkenes (unsaturated hydrocarbons)**
  - (a) Describe alkenes as a homologous series with a double bond and the general formula CnH2n.
  - (b) Be able to name, or recognise from the name, C2 to C6 straight-chain alkenes, including the position of the double bond.
  - (c) Recognise and be able to use the test for unsaturation with bromine water.
  - (d) Know that addition reactions take place with the following substances: hydrogen, halogens, hydrogen halides and steam. Be able to write the balanced chemical equations for these reactions and recognise the formulae of the products formed. (Mechanisms and consideration of carbocation stability are no
- **C13.4: Polymers**
  - (a) Addition polymerisation, polyalkenes: i. Know that alkenes or other molecules with a C=C bond may react with each other to form long-chain saturated molecules called polymers by addition reactions called polymerisation, and that the unsaturated molecules are called monomers. ii. If given an unsatura
  - (b) Condensation polymerisation, polyesters and polyamides (to include amino acids forming proteins):
- **C13.5: Alcohols**
  - (a) Describe alcohols as a homologous series with the general formula CnH2n+1OH.
  - (b) Be able to name, or recognise from the name, C1 to C6 straight-chain alcohols, including the position of the -OH group.
  - (c) Describe the reaction of alcohols with sodium metal.
- **C13.6: Carboxylic acids**
  - (a) Describe carboxylic acids as a homologous series with the general formula CnH2n+1COOH.
  - (b) Be able to name, or recognise from the name, C1 to C6 straight-chain carboxylic acids.
  - (c) Describe the chemical properties of carboxylic acids as those of weak acids, and so be able to predict their reactions and determine the formulae of their salts.
  - (d) Know that carboxylic acids react with alcohols in the presence of an acid catalyst to produce esters. The naming system (nomenclature) of the alcohols involves all previous rules, and the following additional rules apply:

### C14: Metals

- **C14.1: Understand that the reactivity of a metal is linked to its tendency to form positive ions and the ease of extraction of the metal.**
  - Understand that the reactivity of a metal is linked to its tendency to form positive ions and the ease of extraction of the metal.
- **C14.2: Be able to use displacement reactions to establish the order of reactivity of metals and vice versa.**
  - Be able to use displacement reactions to establish the order of reactivity of metals and vice versa.
- **C14.3: Describe how the uses of metals are related to their physical and chemical properties, e.g.**
  - Describe how the uses of metals are related to their physical and chemical properties, e.g.
  - Al, Fe, Cu, Ag, Au, Ti, and understand that alloys can be formed to produce materials with specific properties.
- **C14.4: Know that most metal ores are the oxides of the metal, and that the extraction of metals always involves reduction processes.**
  - Know that most metal ores are the oxides of the metal, and that the extraction of metals always involves reduction processes.
- **C14.5: Know that common properties of transition metals include**
  - (a) they are able to form stable ions in different oxidation states
  - (b) they often form coloured compounds
  - (c) they are often used as catalysts (as ions or atoms). A collection of metals (from bottom left: copper, aluminium, zinc, iron and lead)

### C15: Kinetic/Particle theory

- **C15.1: Be able to describe the packing and movement of particles in the three states of matter: solid, liquid and gas.**
  - Be able to describe the packing and movement of particles in the three states of matter: solid, liquid and gas.
- **C15.2: Understand the changes to the packing and movement of particles in the following changes of state: freezing, melting, boiling/evaporating, and condens**
  - Understand the changes to the packing and movement of particles in the following changes of state: freezing, melting, boiling/evaporating, and condensing.
  - Understand that the energy required for these processes is related to the bonding and structure of the substance, including a consideration of intermolecular forces.
  - The three states of matter We classify objects and materials around us as solids, liquids and gases based on their properties.
  - Some of the characteristic properties of the three states of matter are shown in the table.
  - property solid liquid

### C16: Chemical tests

- **C16.1: Know and recognise the following tests for gases**
  - (a) hydrogen – explodes with a ‘squeaky pop’ when a burning splint is held at the open end of a test tube
  - (b) oxygen – relights a glowing splint
  - (c) carbon dioxide – limewater turns cloudy when shaken with the gas
  - (d) chlorine – damp blue litmus paper turns red and then is bleached (paper turns white)
- **C16.2: Know, recognise and describe the following tests for the anions**
  - (a) carbonates – using a dilute acid
  - (b) halides – using an aqueous solution of silver nitrate in the presence of dilute nitric acid (chlorides form a white precipitate; bromides form a cream precipitate; iodides form a yellow precipitate)
  - (c) sulfates – using an aqueous solution of barium chloride in the presence of dilute hydrochloric acid
- **C16.3: Know and recognise the test for the following metal cations using aqueous sodium hydroxide**
  - (a) Al3+, Ca2+ and Mg2+ each form a white precipitate.
  - (b) Cu2+ forms a blue precipitate.
  - (c) Fe2+ forms a green precipitate.
  - (d) Fe3+ forms a brown precipitate.
- **C16.4: Recall and recognise the flame test for the cations of the following metals: Li (crimson red), Na (yellow-orange), K (lilac), Ca (red-orange), Cu (gre**
  - Recall and recognise the flame test for the cations of the following metals: Li (crimson red), Na (yellow-orange), K (lilac), Ca (red-orange), Cu (green).
- **C16.5: Know and recognise the test for the presence of water using anhydrous copper(II) sulfate (colour change from white to blue).**
  - Know and recognise the test for the presence of water using anhydrous copper(II) sulfate (colour change from white to blue).
  - A chemical test is a chemical reaction that is used to identify a substance.
  - Chemical tests, which are often completed in a test tube, can be described as qualitative or quantitative.
  - Each test exploits a reaction of the substance that leads to a specific observation such as precipitation (production of an insoluble substance), effervescence (bubbling/fizzing), a temperature change, a colour change, and so on.
  - Some tests are specific and can identify a single substance, but some are more generic and identify the general type of substance such as an acid or an alkali.
  - By combining tests, many simple compounds can be identified.

### C17: Air and water

- **C17.1: Know and be able to use the composition of dry air, and understand that fractional distillation can be used to separate the components of air.**
  - Know and be able to use the composition of dry air, and understand that fractional distillation can be used to separate the components of air.
- **C17.2: Know the origins and describe the effects of greenhouse gases such as CO2 and CH4.**
  - Know the origins and describe the effects of greenhouse gases such as CO2 and CH4.
- **C17.3: Know the origins and effects of gaseous pollutants such as CO, CO2, SO2 and NOx.**
  - Know the origins and effects of gaseous pollutants such as CO, CO2, SO2 and NOx.
- **C17.4: Know the purpose of chlorine and fluoride ions in the treatment of drinking water.**
  - Know the purpose of chlorine and fluoride ions in the treatment of drinking water.
  - Fractional distillation of air In industry, the gases in air are separated by a fractional distillation process.
  - Fractional distillation is a process by which liquids with different boiling points are separated.
  - So first the air has to be cold enough for all of it to condense into a liquid.
  - It has to be cooled to a temperature below −200 °C.
  - This cooling is done by first compressing the air to 150 times atmospheric pressure.
  - This actually warms the air up, so the pressurised air is cooled back down by passing the air over pipes carrying cold water.
  - The main cooling takes place when the pressure is released and as this happens the air expands rapidly – similar to what happens when an aerosol is sprayed from a deodorant can.


## Module B: Biology

### B1: Cells

- **B1.1: Know and understand the structure and function of the main sub-cellular components of eukaryotic cells (both animal and plant) including**
  - (a) cell membrane
  - (b) cytoplasm
  - (c) nucleus
  - (d) mitochondrion
  - (e) cell wall (plant only)
  - (f) chloroplast (plant only)
  - (g) vacuole (plant only)
- **B1.2: Know and understand the structure and function of the main sub-cellular components of prokaryotic cells (bacteria) including**
  - (a) cell membrane
  - (b) cytoplasm
  - (c) cell wall
  - (d) chromosomal DNA/no ‘true’ nucleus
  - (e) plasmid DNA
- **B1.3: Know and understand the levels of organisation within organisms as: cells to tissues to organs to organ systems.**
  - Know and understand the levels of organisation within organisms as: cells to tissues to organs to organ systems.
  - All living things are made up of one or more units called cells.
  - Cells are microscopic.
  - Eukaryotes are organisms made up of a cell or cells containing DNA inside a recognisable nucleus.
  - The DNA is present in the form of one or more linear chromosomes within the nucleus.
  - A unicellular organism or single-celled organism is an organism that consists of only one cell.
  - Multicellular organisms are made up of many cells.
  - These may be specialised to perform particular functions.

### B2: Movement across membranes

- **B2.1: Know and understand the processes of diffusion, osmosis (in terms of water potential), and active transport, including examples in living and non-livi**
  - Know and understand the processes of diffusion, osmosis (in terms of water potential), and active transport, including examples in living and non-living systems.
  - sugar molecules to diffuse.
  - Eventually the sugar molecules will become evenly distributed in the water.
  - Sugar molecules in water If a cell is placed in a situation where there is a higher concentration of molecules outside the cell, the process of diffusion could result in a net movement of the molecules into the cell.
  - However, this depends on whether the cell membrane will let the molecules through.
  - This is because cell membranes are partially permeable.
  - This means they allow some substances to move across but not other substances.

### B3: Cell division and sex determination

- **B3.1: Mitosis and the cell cycle**
  - (a) Know and understand that the mitotic cell cycle includes interphase (involving cell growth and DNA replication) and mitosis (involving one cell division leading to two daughter cells which are genetically identical to each other and to the parental cell).
  - (b) Know and understand the importance of mitosis in the growth of an organism: specifically, its roles in increasing the number of cells, repairing tissues, replacing cells and asexual reproduction.
  - (c) Know and understand that cancer is the result of changes in cells, including mutations, that lead to uncontrolled cell division.
- **B3.2: Meiosis and the cell cycle**
  - (a) Know and understand that the meiotic cell cycle includes interphase (involving cell growth and DNA replication) and meiosis (involving two cell divisions leading to four daughter cells, each with a single copy of each chromosome).
  - (b) Know and understand the role of meiosis in producing genetically different haploid gametes so that the zygote (fertilised egg cell) produced at fertilisation is diploid.
- **B3.3: Asexual and sexual reproduction**
  - (a) Know and understand that asexual reproduction involves one parent and that offspring are genetically identical when no mutations occur.
  - (b) Know and understand that sexual reproduction involves two parents and that offspring are genetically different in relation to each other and the parents, leading to (increased) variation.
- **B3.4: Sex determination**
  - (a) Know that, in most mammals including humans, females are XX and males are XY.
  - (b) Analyse genetic data and diagrams to establish the sex and ratio of offspring. Growth All living organisms grow during their lifetime. Humans are multicellular organisms; our bodies are made up of trillions of cells. Every human begins life as a single cell, a zygote (fertilised egg cell). The zygot

### B4: Inheritance

- **B4.1: Know and understand the nucleus as a site of genetic material in eukaryotic cells.**
  - Know and understand the nucleus as a site of genetic material in eukaryotic cells.
- **B4.2: Know and understand the following genetic terms**
  - (a) gene
  - (b) allele
  - (c) dominant
  - (d) recessive
  - (e) heterozygous
  - (f) homozygous
  - (g) phenotype
  - (h) genotype i. chromosome
- **B4.3: Monohybrid crosses**
  - (a) Use and interpret genetic data and diagrams involving monohybrid (single gene) crosses.
  - (b) Use and interpret family trees/pedigrees and express outcomes as ratios, numbers, probabilities or percentages.
  - (c) Understand the concept of inherited conditions.
  - (d) Know that most phenotypes are the result of multiple genes and only some result from single gene inheritance. Chromosomes and genes Most animal and plant cells contain a nucleus which controls the activities of the cell.

### B5: DNA

- **B5.1: Know and understand that**
  - (a) the genome is the full set of genetic material (DNA) of an organism.
  - (b) this DNA is contained within chromosomes.
- **B5.2: Know and understand the structure of DNA**
  - (a) Know and understand that single-stranded DNA (ssDNA) is a polymer made up of nucleotides joined together to form one strand of DNA.
  - (b) Know and understand that double-stranded DNA (dsDNA) is a polymer made up of two strands of DNA forming a double helix.
  - (c) Know and understand that the structure of each nucleotide consists of a common sugar and phosphate group as well as one of four different nitrogenous bases.
  - (d) Know the complementary pairs of DNA nitrogenous bases – adenine (A) pairs with thymine (T) and guanine (G) pairs with cytosine (C) – and that the
- **B5.3: Protein synthesis**
  - (a) Know and understand that protein synthesis involves producing chains of amino acids called polypeptides.
  - (b) Know and understand that one or more polypeptide(s) can form a functional protein.
  - (c) Know and understand that the three-dimensional shape of a protein is determined by the sequence of its amino acids.
  - (d) Know and understand that the sequence of nucleotide bases in a gene determines the sequence of amino acids in the polypeptide the gene codes for.
- **B5.4: Gene mutations**
  - (a) Understand that a mutation changes the sequence of nucleotides in the DNA.
  - (b) Know that most mutations have no effect on the phenotype, some will have a small effect, whilst occasionally others will determine the phenotype. This allows one DNA molecule from each chromosome to be passed to each new daughter cell when the cell divides. A DNA molecule is very large, and so a chr

### B6: Gene technologies

- **B6.1: Genetic engineering**
  - (a) Understand the process of genetic engineering to include: i. taking a copy of a gene from the DNA of one organism ii. insertion of that gene into the DNA of another organism iii. the roles of restriction enzymes and ligases in recombining DNA.
  - (b) Recall and interpret examples of genetic engineering in different cell types.
  - (c) Explain the benefits and risks of using genetic engineering in medical applications.
- **B6.2: Stem cells**
  - (a) Know and understand that some early embryonic cells are totipotent and have the potential to develop into a complete multicellular organism.
  - (b) Know and understand that most embryonic stem cells are pluripotent and can differentiate into any cell type.
  - (c) Know and understand that adult stem cells are multipotent and can differentiate into a limited number of different cell types.
  - (d) Know and understand the likely benefits and risks of using stem cells in medical applications.
- **B6.3: Selective breeding**
  - (a) Know and understand the differences and similarities between natural selection and selective breeding.
  - (b) Understand the impact of selective breeding on populations. Genetic engineering Genetic engineering involves taking a copy of a gene from one organism and inserting that gene into the DNA of another organism, to create a genetically modified organism (GMO) or a transgenic organism. The first GMOs we

### B7: Variation

- **B7.1: Natural selection and evolution**
  - (a) Know that there is usually extensive genetic variation within a population of a species.
  - (b) Describe evolution as a change in the inherited characteristics of a population over time through a process of natural selection which may result in the formation of a new species.
  - (c) Know and understand how evolution can occur through natural selection of variants that give rise to phenotypes best suited to their environment.
  - (d) Know and understand that antibiotic resistance in bacteria is an example of evolution through natural selection.
- **B7.2: Sources of variation**
  - (a) Understand that variation can be genetic/inherited, resulting in a range of phenotypes.
  - (b) Understand that variation can also be environmental, which affects a range of phenotypes. The blackbird and robin are different species of bird. Genetic variation Natural selection is the process whereby some organisms (variants) in a population are preferentially selected for and others selected ag

### B8: Enzymes

- **B8.1: Know and understand that enzymes are primarily proteins that function as biological catalysts.**
  - Know and understand that enzymes are primarily proteins that function as biological catalysts.
- **B8.2: Know and understand the general mechanism of enzyme action, including the role of the active site and enzyme specificity.**
  - Know and understand the general mechanism of enzyme action, including the role of the active site and enzyme specificity.
- **B8.3: Know and understand how the factors of temperature and pH can affect the rate of enzyme action.**
  - Know and understand how the factors of temperature and pH can affect the rate of enzyme action.
- **B8.4: Know the role of amylases, proteases and lipases in the digestion of carbohydrates, proteins and fats.**
  - Know the role of amylases, proteases and lipases in the digestion of carbohydrates, proteins and fats.
  - Enzymes convert molecules (substrates) into different molecules known as products.
  - Enzyme + substrate is called an enzyme substrate complex (ESC).
  - The enzyme is unchanged by the reaction.
  - An enzyme may act on one substrate to form two products or it may join two substrates to form one product.
  - The enzyme is not used up during the reaction and can be used again.
  - Breaking substrates and making products A substrate may be broken by the addition of water = hydrolysis reaction.
  - A product may be formed by the removal of water = condensation reaction.

### B9: Animal physiology

- **B9.1: Respiration**
  - (a) Know and understand the process of cellular respiration in living cells.
  - (b) Know and understand the process of aerobic respiration in living cells, including the word equation.
  - (c) Know and understand the process of anaerobic respiration in animal cells, including the word equation. Glucose  →  Lactic acid  +  Energy (ATP) Lactic acid is a toxic molecule and so this must be removed from the body. Respiration and exercise When an animal (including humans) starts to exercise, mu
- **B9.2: Organ systems**
  - (a) Nervous system: i. Know and understand that the central nervous system comprises the brain and spinal cord. ii. Know and understand the structure and function of sensory neurones, relay neurones, motor neurones, synapses and the reflex arc. Which of these statements about the nervous system is corre
- **B9.3: Homeostasis**
  - (a) Know that homeostasis is the maintenance of a constant internal environment, and appreciate its importance in multicellular animals.
  - (b) Understand the concept of negative feedback in the context of homeostasis.
  - (c) Know and understand the regulation of blood glucose levels, including the role of insulin and glucagon.
  - (d) Understand the main features of type 1 and type 2 diabetes, and how type 1 diabetes can be treated.
  - (e) Know and understand the regulation of water content (including the role of ADH) and the regulation of body temperature. The regulation of blood glucose levels
- **B9.4: Hormones**
  - (a) Know and understand that hormones are released from specific endocrine glands and travel via the blood to their target structures.
  - (b) Know and understand the main role of adrenaline in the body.
- **B9.5: Disease and body defence**
  - (a) Communicable diseases: i.  Know that communicable diseases are caused by pathogenic bacteria, viruses, protists and fungi. ii.  Understand the transmission routes of sexually transmitted infections, including the effect on the immune system of HIV which results in AIDS. iii. Understand the treatment

### B10: Ecosystems

- **B10.1: Levels of organisation in an ecosystem**
  - (a) Know and understand the organisation of levels within an ecosystem from individuals through to populations, and from communities through to ecosystems.
  - (b) Know and understand how communities can be affected by abiotic and biotic factors.
  - (c) Know and understand the factors that can cause a population to change in size.
  - (d) Understand the importance of interdependence in ecosystems (relating to predation, mutualism and parasitism) and of competition in a community.
  - (e) Know and understand that photosynthetic organisms are the primary producers of food in an ecosystem, and therefore biomass. It is worthwhile learning the definition of each of the key terms:
- **B10.2: Material cycling**
  - (a) Know and understand the carbon cycle, including the importance of the following processes: i.  photosynthesis ii.  respiration iii.  combustion iv.  decomposition
  - (b) Understand the importance of the water cycle to living organisms. Processes involved in the carbon cycle Photosynthesis Photosynthesis is a process carried out by green plants and some types of bacteria. They take
- **B10.3: Biodiversity**
  - (a) Know and understand how quadrats and belt transects are used to investigate the distribution and abundance of organisms in a habitat, and interpret data from their use.
  - (b) Know and understand how to determine the number of organisms in a given area.
  - (c) Know and understand the positive and negative human interactions in an ecosystem, including fish farming, acid rain and eutrophication, and explain their impact on biodiversity. How to assess the abundance of a species in an area The area, such as a field, may be large so an estimate has to made. A 

### B11: Plant physiology

- **B11.1: Importance of photosynthesis**
  - (a) Know and understand the process of photosynthesis as an endothermic reaction that uses light energy to react carbon dioxide and water to produce glucose and oxygen.
  - (b) Understand the effect of temperature, light intensity and carbon dioxide concentration as limiting factors on the rate of photosynthesis.
- **B11.2: Transport systems in plants**
  - (a) Know and understand how the structures of xylem and phloem are adapted to their functions in plants, including the role of:


---
*5 modules, 50 topics, 270 subtopics, 948 skills*