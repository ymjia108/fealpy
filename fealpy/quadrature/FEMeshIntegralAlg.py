import numpy as np
from scipy.sparse import csr_matrix

def broadcast(c, phi):
    """
    Notes
    -----

    把 c 的形状广播为与 phi 相关的形状

    phi: ijk....
    c : 
    """


class FEMeshIntegralAlg():
    def __init__(self, mesh, q, cellmeasure=None):
        self.mesh = mesh
        self.integrator = mesh.integrator(q, 'cell')

        self.cellintegrator = self.integrator
        self.cellbarycenter =  mesh.entity_barycenter('cell')
        self.cellmeasure = cellmeasure if cellmeasure is not None else mesh.entity_measure('cell')

        self.edgemeasure = mesh.entity_measure('edge')
        self.edgebarycenter = mesh.entity_barycenter('edge')
        self.edgeintegrator = mesh.integrator(q, 'edge')

        GD = mesh.geo_dimension()
        if GD == 3:
            self.facemeasure = mesh.entity_measure('face')
            self.facebarycenter = mesh.entity_measure('face')
            self.faceintegrator = mesh.integrator(q, 'face') 
        else:
            self.facemeasure = self.edgemeasure
            self.facebarycenter = self.edgebarycenter
            self.faceintegrator = self.edgeintegrator

    def construct_matrix(self, basis0, 
            basis1=None,  c=None, 
            cell2dof0=None, gdof0=None, 
            cell2dof1=None, gdof1=None, 
            q=None):
        """

        Parameters
        ---------

        c: 

        Notes
        -----

        给定两个空间的基函数, 组装对应的离散算子. 
        """

        mesh = self.mesh
        qf = self.integrator if q is None else mesh.integrator(q, 'cell')
        bcs, ws = qf.get_quadrature_points_and_weights()

        ps = mesh.bc_to_point(bcs)
        if basis0.coordtype == 'barycentric':
            phi0 = basis0(bcs) # (NQ, NC, ldof, ...)
        elif basis0.coordtype == 'cartesian':
            phi0 = basis0(ps)

        if basis1 is not None:
            if basis1.coordtype == 'barycentric':
                phi1 = basis1(bcs) # (NQ, NC, ldof, ...)
            elif basis1.coordtype == 'cartesian':
                phi1 = basis1(ps)
        else:
            phi1 = phi0

        if c is None:
            M = np.einsum('i, ijk..., ijm..., j->jkm', ws, phi0, phi1,
                    self.cellmeasure, optimize=True)
        else: # TODO: make here work
            if isinstance(c, (int, float)):
                M = np.einsum('i, ijk..., ijm..., j->jkm', c*ws, phi0, phi1,
                        self.cellmeasure, optimize=True)
            elif callable(c):
                if c.coordtype == 'barycentric':
                    c = c(bcs)
                elif c.coordtype == 'cartesian':
                    c = c(ps)

                if isinstance(c, (int, float)):
                    M = np.einsum('i, ijk..., ijm..., j->jkm', c*ws, phi0, phi1,
                            self.cellmeasure, optimize=True)
                elif isinstance(c, np.ndarray):
                    # user should make `c` have the correct shape
                    if len(c.shape) == 2:
                        M = np.einsum('i, ij, ijk..., ijm..., j->jkm', ws, c, phi0, phi1,
                                self.cellmeasure, optimize=True)
                    elif len(c.shape) == 3:
                        M = np.einsum('i, ijk..., ijk..., ijm..., j->jkm', ws, c[:, :, None, :], phi0, phi1,
                                self.cellmeasure, optimize=True)
                    elif len(c.shape) == 4:
                        M = np.einsum('i, ijkab, ijkb, ijma, j->jkm', ws, c[:, :, None, :, :], phi0, phi1,
                                self.cellmeasure, optimize=True)

        if cell2dof0 is None: # just construct cell matrix
            return M

        gdof0 = gdof0 or cell2dof0.max()
        if cell2dof1 is None:
            gdof1 = gdof0
            cell2dof1 = cell2dof0
        else:
            gdof1 = gdof1 or cell2dof1.max()

        I = np.broadcast_to(cell2dof0[:, :, None], shape=M.shape)
        J = np.broadcast_to(cell2dof1[:, None, :], shape=M.shape)

        M = csr_matrix((M.flat, (I.flat, J.flat)), shape=(gdof0, gdof1))

        return M

    def construct_vector_s_s(self, f, basis, cell2dof, gdof=None, q=None):
        """
        Notes
        -----
        f 是标量函数
        basis 是标量函数
        """
        mesh = self.mesh
        qf = self.integrator if q is None else mesh.integrator(q, 'cell')
        bcs, ws = qf.get_quadrature_points_and_weights()
        ps = mesh.bc_to_point(bcs, etype='cell')

        if basis.coordtype == 'barycentric':
            phi = basis(bcs)
        elif basis.coordtype == 'cartesian':
            phi = basis(ps)

        if callable(f):
            if f.coordtype == 'barycentric':
                val = f(bcs)
            elif f.coordtype == 'cartesian':
                val = f(ps)
        else:
            #TODO: f 可以是多种形式的, 函数, 数组 
            val = f

        #TODO: consider more case
        bb = np.einsum('i, ij, ijk, j->jk', ws, val, phi, self.cellmeasure)

        gdof = gdof or cell2dof.max()
        shape = (gdof, )
        b = np.zeros(shape, dtype=phi.dtype)
        np.add.at(b, cell2dof, bb)
        return b

    def construct_vector_v_v(self, f, basis, cell2dof, gdof=None, q=None):
        """
        Notes
        -----
        f 是向量函数
        basis 是向量函数
        """
        mesh = self.mesh
        qf = self.integrator if q is None else mesh.integrator(q, 'cell')
        bcs, ws = qf.get_quadrature_points_and_weights()
        ps = mesh.bc_to_point(bcs, etype='cell')

        if basis.coordtype == 'barycentric':
            phi = basis(bcs)
        elif c.coordtype == 'cartesian':
            phi = basis(ps)

        if callable(f):
            if f.coordtype == 'barycentric':
                val = f(bcs)
            elif f.coordtype == 'cartesian':
                val = f(ps)

            if len(val.shape) == 1: # (GD, )
                val = val[None, None, :]
        elif isinstance(f, np.ndarray):
            val = f[None, None, :]

        bb = np.einsum('i, ij..., ijk..., j->jk',
                ws, val, phi, self.cellmeasure)

        gdof = gdof or cell2dof.max()
        shape = (gdof, val.shape[-1])
        b = np.zeros(shape, dtype=phi.dtype)
        np.add.at(b, (cell2dof, np.s_[:]), bb)
        return b

    def construct_vector_v_s(self, f, basis, cell2dof, gdof=None, q=None):
        """

        Notes
        -----
        f 是向量函数
        basis 是标量函数
        """
        mesh = self.mesh
        qf = self.integrator if q is None else mesh.integrator(q, 'cell')
        bcs, ws = qf.get_quadrature_points_and_weights()
        ps = mesh.bc_to_point(bcs, etype='cell')

        if basis.coordtype == 'barycentric':
            phi = basis(bcs)
        elif c.coordtype == 'cartesian':
            phi = basis(ps)

        if callable(f):
            if f.coordtype == 'barycentric':
                val = f(bcs)
            elif f.coordtype == 'cartesian':
                val = f(ps)
            bb = np.einsum('i, ij, ijk, j->jk',
                    ws, val, phi, self.cellmeasure)
        elif isinstance(f, (int, float)):
            bb = np.einsum('m, mik, i->ik',
                    f*ws, phi, self.cellmeasure)

        gdof = gdof or cell2dof.max()
        shape = (gdof, val.shape[-1])
        b = np.zeros(shape, dtype=phi.dtype)
        np.add.at(b, (cell2dof, np.s_[:]), bb)

        return b


    def edge_integral(self, u, edgetype=False, q=None, barycenter=True):
        mesh = self.mesh

        qf = self.edgeintegrator if q is None else mesh.integrator(q, 'edge')
        bcs, ws = qf.quadpts, qf.weights

        if barycenter:
            val = u(bcs)
        else:
            ps = mesh.bc_to_point(bcs, etype='edge')
            val = u(ps)

        if edgetype is True:
            e = np.einsum('i, ij..., j->j...', ws, val, self.edgemeasure)
        else:
            e = np.einsum('i, ij..., j->...', ws, val, self.edgemeasure)
        return e

    def face_integral(self, u, facetype=False, q=None, barycenter=True):
        mesh = self.mesh

        qf = self.faceintegrator if q is None else mesh.integrator(q, 'face')
        bcs, ws = qf.quadpts, qf.weights

        if barycenter:
            val = u(bcs)
        else:
            ps = mesh.bc_to_point(bcs, etype='face')
            val = u(ps)

        dim = len(ws.shape)
        s0 = 'abcde'
        s1 = '{}, {}j..., j->j...'.format(s0[0:dim], s0[0:dim])
        if facetype is True:
            e = np.einsum(s1, ws, val, self.facemeasure)
        else:
            e = np.einsum(s1, ws, val, self.facemeasure)
        return e

    def cell_integral(self, u, celltype=False, q=None, barycenter=True):
        mesh = self.mesh

        qf = self.integrator if q is None else mesh.integrator(q, 'cell')
        bcs, ws = qf.quadpts, qf.weights

        if barycenter:
            val = u(bcs)
        else:
            ps = mesh.bc_to_point(bcs, etype='cell')
            val = u(ps)
        dim = len(ws.shape)
        s0 = 'abcde'
        s1 = '{}, {}j..., j->j...'.format(s0[0:dim], s0[0:dim])
        if celltype is True:
            e = np.einsum(s1, ws, val, self.cellmeasure)
        else:
            e = np.einsum(s1, ws, val, self.cellmeasure)
        return e

    def integral(self, u, celltype=False, barycenter=True):
        """
        """
        qf = self.integrator
        bcs = qf.quadpts # 积分点 (NQ, 3)
        ws = qf.weights # 积分点对应的权重 (NQ, )
        if barycenter:
            val = u(bcs)
        else:
            ps = self.mesh.bc_to_point(bcs) # (NQ, NC, 2)
            val = u(ps)
        dim = len(ws.shape)
        s0 = 'abcde'
        s1 = '{}, {}j..., j->j...'.format(s0[0:dim], s0[0:dim])
        e = np.einsum(s1, ws, val, self.cellmeasure)
        if celltype is True:
            return e
        else:
            return e.sum()

    def L2_norm(self, uh, celltype=False):
        def f(x):
            return uh(x)**2
        e = self.integral(f, celltype=celltype)
        if celltype is False:
            return np.sqrt(e.sum())
        else:
            return np.sqrt(e)

    def L2_norm_1(self, uh, celltype=False):
        def f(x):
            return np.sum(uh**2, axis=-1)*self.cellmeasure

        e = self.integral(f, celltype=celltype)
        if celltype is False:
            return np.sqrt(e.sum())
        else:
            return np.sqrt(e)

    def L1_error(self, u, uh, celltype=False):
        def f(x):
            xx = self.mesh.bc_to_point(x)
            return np.abs(u(xx) - uh(x))
        e = self.integral(f, celltype=celltype)
        if celltype is False:
            return e.sum()
        else:
            return e
        return

    def L2_error(self, u, uh, celltype=False):
        def f(bc):
            xx = self.mesh.bc_to_point(bc)
            return (u(xx) - uh(bc))**2
        e = self.integral(f, celltype=celltype)
        if celltype is False:
            return np.sqrt(e.sum())
        else:
            return np.sqrt(e)
        return 

    def L2_error_uI_uh(self, uI, uh, celltype=False):
        def f(x):
            return (uI(x) - uh(x))**2
        e = self.integral(f, celltype=celltype)
        if celltype is False:
            return np.sqrt(e.sum())
        else:
            return np.sqrt(e)
        return 

    def Lp_error(self, u, uh, p, celltype=False):
        def f(x):
            xx = self.mesh.bc_to_point(x)
            return np.abs(u(xx) - uh(x))**p
        e = self.integral(f, celltype=celltype)
        if celltype is False:
            return e.sum()**(1/p)
        else:
            return e**(1/p)
        return 
