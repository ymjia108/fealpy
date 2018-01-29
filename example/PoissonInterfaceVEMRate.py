import numpy as np
import sys

from fealpy.model.poisson_interface_model_2d import CircleInterfaceData, Circle1InterfaceData, SquareInterfaceData
from fealpy.vemmodel import PoissonVEMModel
from fealpy.mesh.adaptive_tools import AdaptiveMarker
from fealpy.tools.show import showmultirate
from fealpy.quadrature import QuadrangleQuadrature

from fealpy.mesh.implicit_curve import Circle
from fealpy.mesh.adaptive_interface_mesh_generator import AdaptiveMarker2d, QuadtreeInterfaceMesh2d 

import matplotlib.pyplot as plt 
from mpl_toolkits.mplot3d import Axes3D

m = int(sys.argv[1])
maxit = int(sys.argv[2])
theta = float(sys.argv[3])

if m == 1:
    model = CircleInterfaceData([0,0],2,1,1)
    quadtree = model.init_mesh(n=4, meshtype='quadtree')
if m == 2:
    model = Circle1InterfaceData([0,0],2,1,1,0.001, 3)
    quadtree = model.init_mesh(n=4, meshtype='quadtree')
if m == 3:
    model = SquareInterfaceData([0,0],2,2,1)
    quadtree = model.init_mesh(n=4, meshtype='quadtree')

k = maxit - 10
errorType = ['$\| u_I - u_h \|_{l_2}$',
             '$\|\\nabla u_I - \\nabla u_h\|_A$',
             '$\| u - \Pi^\Delta u_h\|_0$',
             '$\|\\nabla u - \\nabla\Pi^\Delta u_h\|$',
             '$\|\\nabla\Pi^\Delta u_h -\Pi^\DeltaG(\\nabla\Pi^\Delta u_h)\|$'
            ]
Ndof = np.zeros((maxit,), dtype=np.int)
errorMatrix = np.zeros((len(errorType), maxit), dtype=np.float)


marker = AdaptiveMarker2d(phi, maxh=0.1, maxa=2)
alg = QuadtreeInterfaceMesh2d(mesh, marker)
pmesh= alg.get_interface_mesh()
vem = PoissonVEMModel(model, mesh, p=1, integrator=integrator)

for i in range(maxit):
    print('step:', i)
    vem.solve()
    eta = vem.recover_estimate()
    Ndof[i] = vem.V.number_of_global_dofs()
    errorMatrix[0, i] = vem.l2_error()
    errorMatrix[1, i] = vem.uIuh_error() 
    errorMatrix[2, i] = vem.L2_error(quadtree)
    errorMatrix[3, i] = vem.H1_semi_error(quadtree)
    errorMatrix[4, i] = np.sqrt(np.sum(eta**2))
    if i < maxit - 1:
        quadtree.refine(marker=AdaptiveMarker(eta, theta=theta))
        vem.reinit(quadtree.to_pmesh())


mesh = vem.V.mesh
fig1 = plt.figure()
fig1.set_facecolor('white')
axes = fig1.gca() 
mesh.add_plot(axes, cellcolor='w')

fig2 = plt.figure()
fig2.set_facecolor('white')
axes = fig2.gca(projection='3d')
x = mesh.point[:, 0]
y = mesh.point[:, 1]
tri = quadtree.leaf_cell(celltype='tri')
axes.plot_trisurf(x, y, tri, vem.uh, cmap=plt.cm.jet, lw=0.0)


fig3 = plt.figure()
fig3.set_facecolor('white')
axes = fig3.gca()
optionlist = ['k-*', 'b-o', 'r--^', 'g->', 'm-8', 'c-D','y-x', 'y-+', 'y-h', 'y-p']
showmultirate(axes, k, Ndof, errorMatrix[:4, :], optionlist[:4], errorType[:4])
axes.legend(loc=3, prop={'size': 30})
plt.show()
